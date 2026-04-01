"""Conflict Detector agent — flags TV analyst calls contradicted by data (Section S10)."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.models import ConflictFlag
from agents.prompts.conflict import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_conflict_agent(state: AgentState) -> Dict[str, Any]:
    """Detect contradictions between TV analyst calls and quantitative data."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    tv_calls = features.tv_analyst_calls

    if not tv_calls:
        logger.info("Conflict agent: no TV analyst calls, skipping")
        return {"conflict_flags": []}

    logger.info("Conflict agent: checking {} TV calls against data", len(tv_calls))

    try:
        tv_calls_json = json.dumps(
            [c.model_dump() for c in tv_calls], indent=2, default=str
        )
        candidates_json = json.dumps(
            [c.model_dump(include={"ticker", "gap_pct", "options_skew", "iv_rank",
                                    "fii_holding_change", "delivery_pct"})
             for c in features.gap_up_candidates],
            indent=2, default=str,
        )
        options_json = features.options.model_dump_json(indent=2)
        fii_dii_json = features.fii_dii_history.model_dump_json(indent=2) if features.fii_dii_history else "{}"
        avoid_json = json.dumps(
            [a.model_dump() for a in features.avoid_list], indent=2, default=str
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            tv_calls_json=tv_calls_json,
            candidates_json=candidates_json,
            options_json=options_json,
            fii_dii_json=fii_dii_json,
            avoid_json=avoid_json,
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
            parsed = [parsed] if parsed else []

        flags = [
            ConflictFlag(
                analyst=f.get("analyst", ""),
                call=f.get("call", ""),
                conflict_reason=f.get("conflict_reason", ""),
            )
            for f in parsed
            if f.get("conflict_reason")  # Only include genuine conflicts
        ]

        logger.info("Conflict agent: success — {} conflicts found", len(flags))
        return {"conflict_flags": flags}

    except Exception as e:
        logger.error("Conflict agent failed: {}", e)
        return {"conflict_flags": []}
