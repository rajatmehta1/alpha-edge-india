"""AgentState — shared state flowing through the LangGraph agent graph."""

from __future__ import annotations

from typing import List, TypedDict

from agents.models import (
    ConflictFlag,
    NarrativeOutput,
    ScenarioPlaybook,
    StockAnalysis,
    WatchlistAlertOutput,
)
from features.models import ComputedFeatures


class AgentState(TypedDict, total=False):
    """Mutable state dict passed through every node in the agent graph.

    ``computed_features`` is set once at the start and read by every agent.
    Each agent writes its own output key; fan-in merges all keys.
    """

    # Input — set by the orchestrator before the graph runs
    computed_features: ComputedFeatures

    # Agent outputs
    narrative: NarrativeOutput
    stock_analyses: List[StockAnalysis]
    options_summary: str
    scenario_playbook: ScenarioPlaybook
    conflict_flags: List[ConflictFlag]
    watchlist_alerts: List[WatchlistAlertOutput]
