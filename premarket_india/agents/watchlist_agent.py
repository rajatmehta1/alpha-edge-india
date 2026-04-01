"""Watchlist agent — generates time-sequenced intraday alerts (Section S15)."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.models import WatchlistAlertOutput
from agents.prompts.watchlist import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_watchlist_agent(state: AgentState) -> Dict[str, Any]:
    """Generate 10 time-sequenced watchlist alerts for the trading day."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    logger.info("Watchlist agent: generating intraday alerts")

    try:
        candidates_json = json.dumps(
            [c.model_dump(include={"rank", "ticker", "company", "gap_pct",
                                    "expected_open", "entry_zone_low", "entry_zone_high",
                                    "vwap_pullback", "target_1", "target_2", "stop_loss"})
             for c in features.gap_up_candidates[:5]],
            indent=2, default=str,
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            is_expiry_week=features.expiry.is_expiry_week,
            days_to_expiry=features.expiry.days_to_expiry,
            confidence_score=features.confidence_score,
            nifty_levels_json=features.nifty_levels.model_dump_json(indent=2),
            candidates_json=candidates_json,
            max_pain_nifty=features.options.max_pain_nifty,
            max_pain_banknifty=features.options.max_pain_banknifty,
            pcr=features.options.pcr_near_atm,
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

        alerts = [
            WatchlistAlertOutput(
                time=a.get("time", ""),
                priority=a.get("priority", ""),
                title=a.get("title", ""),
                content=a.get("content", ""),
            )
            for a in parsed[:10]
        ]

        logger.info("Watchlist agent: success — {} alerts", len(alerts))
        return {"watchlist_alerts": alerts}

    except Exception as e:
        logger.error("Watchlist agent failed: {}", e)
        return {"watchlist_alerts": []}
