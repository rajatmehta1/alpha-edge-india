"""Stock Analyst agent — writes catalyst + timing for gap-up candidates (Section S03)."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.models import StockAnalysis
from agents.prompts.stock_analyst import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_stock_analyst_agent(state: AgentState) -> Dict[str, Any]:
    """Generate catalyst and timing text for each gap-up candidate."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    candidates = features.gap_up_candidates

    if not candidates:
        logger.info("Stock analyst agent: no gap-up candidates, skipping")
        return {"stock_analyses": []}

    logger.info("Stock analyst agent: analysing {} candidates", len(candidates))

    try:
        candidates_json = json.dumps(
            [c.model_dump(exclude={"catalyst_text", "timing_text"})
             for c in candidates],
            indent=2, default=str,
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            confidence_score=features.confidence_score,
            candidates_json=candidates_json,
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

        analyses = [
            StockAnalysis(
                ticker=item.get("ticker", ""),
                catalyst_text=item.get("catalyst_text", ""),
                timing_text=item.get("timing_text", ""),
            )
            for item in parsed
        ]

        logger.info("Stock analyst agent: success — {} analyses", len(analyses))
        return {"stock_analyses": analyses}

    except Exception as e:
        logger.error("Stock analyst agent failed: {}", e)
        return {"stock_analyses": []}
