"""LangGraph agent orchestration — sequential fan-out with Groq rate-limit delays.

Due to Groq free-tier limits (30 req/min, ~6k tokens/min), agents run
SEQUENTIALLY with a configurable delay between calls.  Each agent is wrapped
in tenacity retry logic (3 attempts, 5 s exponential backoff).  If an agent
permanently fails, the pipeline continues with empty output for that section.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agents.models import (
    AgentNarratives,
    NarrativeOutput,
    ScenarioPlaybook,
)
from agents.state import AgentState
from config.settings import settings

# ── Import agent functions ──
from agents.narrative_agent import run_narrative_agent
from agents.stock_analyst_agent import run_stock_analyst_agent
from agents.options_agent import run_options_agent
from agents.scenario_agent import run_scenario_agent
from agents.conflict_agent import run_conflict_agent
from agents.watchlist_agent import run_watchlist_agent


# ── Retry-wrapped agent runners ──

def _make_retryable(agent_fn, agent_name: str):
    """Wrap an agent function with tenacity retry and inter-agent delay."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=5, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _call_with_retry(state: AgentState) -> Dict[str, Any]:
        return agent_fn(state)

    def wrapped(state: AgentState) -> Dict[str, Any]:
        try:
            result = _call_with_retry(state)
        except Exception as e:
            logger.error("{} permanently failed after 3 retries: {}", agent_name, e)
            # Return empty output — pipeline continues
            result = agent_fn.__module__  # noqa — unused, just for clarity
            result = _get_empty_fallback(agent_name)

        # Delay before next agent to respect Groq rate limits
        delay = settings.AGENT_DELAY_SECONDS
        if delay > 0:
            logger.debug("Rate-limit delay: sleeping {:.1f}s before next agent", delay)
            time.sleep(delay)

        return result

    wrapped.__name__ = agent_name
    return wrapped


def _get_empty_fallback(agent_name: str) -> Dict[str, Any]:
    """Return the empty/default output for a failed agent."""
    fallbacks = {
        "narrative_agent": {"narrative": NarrativeOutput(
            headline="Market Narrative Unavailable",
            body="The narrative agent could not generate today's summary.",
        )},
        "stock_analyst_agent": {"stock_analyses": []},
        "options_agent": {"options_summary": ""},
        "scenario_agent": {"scenario_playbook": ScenarioPlaybook()},
        "conflict_agent": {"conflict_flags": []},
        "watchlist_agent": {"watchlist_alerts": []},
    }
    return fallbacks.get(agent_name, {})


# ── Build the graph ──

def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph for agent orchestration.

    Topology: sequential chain (due to Groq rate limits).
    ``narrative → stock_analyst → options → scenario → conflict → watchlist``

    Each node reads ``computed_features`` from state and writes its output key.
    """
    graph = StateGraph(AgentState)

    # Register nodes with retry wrappers
    graph.add_node("narrative_agent", _make_retryable(run_narrative_agent, "narrative_agent"))
    graph.add_node("stock_analyst_agent", _make_retryable(run_stock_analyst_agent, "stock_analyst_agent"))
    graph.add_node("options_agent", _make_retryable(run_options_agent, "options_agent"))
    graph.add_node("scenario_agent", _make_retryable(run_scenario_agent, "scenario_agent"))
    graph.add_node("conflict_agent", _make_retryable(run_conflict_agent, "conflict_agent"))
    graph.add_node("watchlist_agent", _make_retryable(run_watchlist_agent, "watchlist_agent"))

    # Sequential edges
    graph.set_entry_point("narrative_agent")
    graph.add_edge("narrative_agent", "stock_analyst_agent")
    graph.add_edge("stock_analyst_agent", "options_agent")
    graph.add_edge("options_agent", "scenario_agent")
    graph.add_edge("scenario_agent", "conflict_agent")
    graph.add_edge("conflict_agent", "watchlist_agent")
    graph.add_edge("watchlist_agent", END)

    return graph


def run_agents(computed_features) -> AgentNarratives:
    """Execute the full agent pipeline and return combined narratives.

    Parameters
    ----------
    computed_features : ComputedFeatures
        The fully-computed feature set from the feature pipeline.

    Returns
    -------
    AgentNarratives
        Combined output from all 6 agents.
    """
    # Fast-fail if no API key — return empty narratives
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_xxx"):
        logger.warning("GROQ_API_KEY not set — skipping AI agents. Report will use data-only sections.")
        return AgentNarratives()

    logger.info("Starting agent orchestration (6 agents, sequential)")
    start = time.time()

    graph = build_agent_graph()
    compiled = graph.compile()

    initial_state: AgentState = {
        "computed_features": computed_features,
    }

    # Execute the graph — LangGraph handles node traversal
    final_state = compiled.invoke(initial_state)

    elapsed = time.time() - start
    logger.info("Agent orchestration complete in {:.1f}s", elapsed)

    # Assemble the combined output
    return AgentNarratives(
        narrative=final_state.get("narrative", NarrativeOutput()),
        stock_analyses=final_state.get("stock_analyses", []),
        options_summary=final_state.get("options_summary", ""),
        scenario_playbook=final_state.get("scenario_playbook", ScenarioPlaybook()),
        conflict_flags=final_state.get("conflict_flags", []),
        watchlist_alerts=final_state.get("watchlist_alerts", []),
    )
