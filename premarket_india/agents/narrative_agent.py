"""Narrative agent — writes the market morning narrative (Section S01)."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.models import NarrativeBullet, NarrativeOutput
from agents.prompts.narrative import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_narrative_agent(state: AgentState) -> Dict[str, Any]:
    """Generate the morning market narrative from computed features."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    logger.info("Narrative agent: generating morning narrative")

    try:
        # Build data payloads for the prompt
        macro_json = features.macro.model_dump_json(indent=2) if features.macro else "{}"
        sector_flows_json = json.dumps(
            [sf.model_dump() for sf in features.sector_flows], indent=2
        )
        gap_up_json = json.dumps(
            [c.model_dump(include={"rank", "ticker", "company", "sector", "gap_pct",
                                    "expected_open", "prev_close", "pattern_match"})
             for c in features.gap_up_candidates[:5]],
            indent=2, default=str,
        )
        options_json = features.options.model_dump_json(indent=2)
        contagion_json = features.contagion_chain.model_dump_json(indent=2)

        # News headlines — use sentiment bundle social items as proxy
        news_items = []
        if hasattr(features, "sentiment") and features.sentiment:
            news_items = features.sentiment.social_items[:10]
        news_json = json.dumps(news_items, indent=2, default=str)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            is_expiry_week=features.expiry.is_expiry_week,
            confidence_score=features.confidence_score,
            macro_json=macro_json,
            sector_flows_json=sector_flows_json,
            gap_up_json=gap_up_json,
            options_json=options_json,
            contagion_json=contagion_json,
            news_json=news_json,
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
        narrative = NarrativeOutput(
            headline=parsed.get("headline", ""),
            body=parsed.get("body", ""),
            bullets=[
                NarrativeBullet(icon=b.get("icon", "M"), text=b.get("text", ""))
                for b in parsed.get("bullets", [])
            ],
        )

        logger.info("Narrative agent: success — headline={!r}", narrative.headline)
        return {"narrative": narrative}

    except Exception as e:
        logger.error("Narrative agent failed: {}", e)
        return {"narrative": NarrativeOutput(
            headline="Market Narrative Unavailable",
            body="The narrative agent could not generate today's summary. "
                 "All data sections below remain fully computed.",
            bullets=[],
        )}
