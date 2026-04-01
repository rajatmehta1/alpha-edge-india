"""Options Flow agent — interprets options positioning (Section S06)."""

from __future__ import annotations

import json
from typing import Any, Dict

from loguru import logger

from agents.json_utils import extract_json
from agents.prompts.options import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.state import AgentState
from config.settings import settings


def run_options_agent(state: AgentState) -> Dict[str, Any]:
    """Generate options flow interpretation narrative."""
    from langchain_groq import ChatGroq
    from datetime import date

    features = state["computed_features"]
    logger.info("Options agent: interpreting flow data")

    try:
        options_json = features.options.model_dump_json(indent=2)
        unusual_json = json.dumps(
            [ua.model_dump() for ua in features.options.unusual_activity],
            indent=2, default=str,
        )
        expiry_json = features.expiry.model_dump_json(indent=2)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            date=date.today().isoformat(),
            is_expiry_week=features.expiry.is_expiry_week,
            days_to_expiry=features.expiry.days_to_expiry,
            options_json=options_json,
            unusual_json=unusual_json,
            expiry_json=expiry_json,
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
        summary = parsed.get("summary", "") if isinstance(parsed, dict) else str(parsed)

        logger.info("Options agent: success")
        return {"options_summary": summary}

    except Exception as e:
        logger.error("Options agent failed: {}", e)
        return {"options_summary": ""}
