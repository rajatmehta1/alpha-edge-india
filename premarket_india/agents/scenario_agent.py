"""Scenario Planner agent — generates 3 if/then playbooks (Section S14)."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.models import ScenarioItem, ScenarioPlaybook
from agents.prompts.scenario import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_scenario_agent(state: AgentState) -> Dict[str, Any]:
    """Generate bull/range/bear scenario playbooks."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    logger.info("Scenario agent: building 3 playbooks")

    try:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            confidence_score=features.confidence_score,
            nifty_levels_json=features.nifty_levels.model_dump_json(indent=2),
            banknifty_levels_json=features.banknifty_levels.model_dump_json(indent=2),
            macro_json=features.macro.model_dump_json(indent=2) if features.macro else "{}",
            options_json=features.options.model_dump_json(indent=2),
            gap_stats_json=features.gap_stats.model_dump_json(indent=2),
            risk_json=features.risk.model_dump_json(indent=2),
        )

        llm = ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS,
            api_key=settings.GROQ_API_KEY,
        )

        response = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])

        parsed = extract_json(response.content)
        if not isinstance(parsed, list):
            parsed = [parsed]

        scenarios = [
            ScenarioItem(
                label=s.get("label", ""),
                color=s.get("color", "var(--phosphor)"),
                probability=s.get("probability", ""),
                trigger=s.get("trigger", ""),
                actions=s.get("actions", ""),
                exit=s.get("exit", ""),
            )
            for s in parsed[:3]
        ]

        playbook = ScenarioPlaybook(scenarios=scenarios)
        logger.info("Scenario agent: success — {} scenarios", len(scenarios))
        return {"scenario_playbook": playbook}

    except Exception as e:
        logger.error("Scenario agent failed: {}", e)
        return {"scenario_playbook": ScenarioPlaybook()}
