"""Contagion chain: rule-based macro catalyst → sector impact chain builder."""

from __future__ import annotations

from loguru import logger

from config.constants import CONTAGION_RULES
from data.models import MacroDashboard
from features.models import ContagionChain, ContagionOrder, ContagionItem


# Thresholds for catalyst detection
_CRUDE_THRESHOLD_PCT = 2.0   # ±2% move in Brent crude
_USDINR_THRESHOLD_PCT = 0.5  # ±0.5% move in USD/INR

# Color mapping for impact
_IMPACT_COLORS = {
    "beneficiaries": "var(--phosphor)",  # Green
    "losers": "var(--red)",
    "neutral": "var(--amber)",
}


def _detect_catalyst(macro: MacroDashboard) -> str | None:
    """Detect the dominant macro catalyst from today's data.

    Returns one of: 'crude_down', 'crude_up', 'fed_dovish', 'inr_weaken', or None.
    """
    crude_pct = macro.brent_crude.change_pct
    usdinr_pct = macro.usdinr.change_pct

    # Priority: crude moves > forex moves > Fed signals
    if crude_pct <= -_CRUDE_THRESHOLD_PCT:
        return "crude_down"
    if crude_pct >= _CRUDE_THRESHOLD_PCT:
        return "crude_up"
    if usdinr_pct >= _USDINR_THRESHOLD_PCT:
        return "inr_weaken"

    # Check for dovish Fed signal via Dow futures rally + USD weakness
    if macro.dow_futures.change_pct > 0.5 and usdinr_pct < -0.2:
        return "fed_dovish"

    return None


def _catalyst_label(catalyst: str) -> str:
    """Human-readable label for the catalyst."""
    labels = {
        "crude_down": "Brent Crude Decline",
        "crude_up": "Brent Crude Rally",
        "fed_dovish": "Fed Dovish Signal",
        "inr_weaken": "INR Depreciation",
    }
    return labels.get(catalyst, catalyst)


def _build_orders(rules: dict) -> list[ContagionOrder]:
    """Build ContagionOrder list from a CONTAGION_RULES entry."""
    order_labels = {
        "1st_order": "1st Order (Direct)",
        "2nd_order": "2nd Order (Indirect)",
        "3rd_order": "3rd Order (Macro)",
    }
    order_colors = {
        "1st_order": "var(--phosphor)",
        "2nd_order": "var(--amber)",
        "3rd_order": "var(--blue, #4a9eff)",
    }

    orders: list[ContagionOrder] = []
    for order_key in ("1st_order", "2nd_order", "3rd_order"):
        if order_key not in rules:
            continue
        order_data = rules[order_key]
        items: list[ContagionItem] = []

        for category in ("beneficiaries", "losers", "neutral"):
            for entry in order_data.get(category, []):
                items.append(ContagionItem(
                    emoji=entry.get("emoji", ""),
                    name=entry.get("name", ""),
                    description=entry.get("desc", ""),
                    impact_color=_IMPACT_COLORS.get(category, "var(--phosphor)"),
                ))

        orders.append(ContagionOrder(
            label=order_labels.get(order_key, order_key),
            color=order_colors.get(order_key, "var(--phosphor)"),
            items=items,
        ))

    return orders


def _build_impact_chart(rules: dict) -> tuple[list[str], list[float], list[str]]:
    """Build impact chart data (labels, scores, colors) for the contagion waterfall chart."""
    labels: list[str] = []
    scores: list[float] = []
    colors: list[str] = []

    for order_key in ("1st_order", "2nd_order", "3rd_order"):
        order_data = rules.get(order_key, {})
        for entry in order_data.get("beneficiaries", []):
            labels.append(entry["name"].split("(")[0].strip())
            scores.append(1.0)
            colors.append("rgba(0,255,65,0.7)")
        for entry in order_data.get("losers", []):
            labels.append(entry["name"].split("(")[0].strip())
            scores.append(-1.0)
            colors.append("rgba(255,59,48,0.7)")
        for entry in order_data.get("neutral", []):
            labels.append(entry["name"].split("(")[0].strip())
            scores.append(0.0)
            colors.append("rgba(255,200,0,0.5)")

    return labels, scores, colors


def compute_contagion_chain(macro: MacroDashboard) -> ContagionChain:
    """Detect dominant catalyst and build rule-based contagion chain.

    This is pure rule-lookup — NO LLM involved.
    """
    logger.info("Computing contagion chain")

    catalyst = _detect_catalyst(macro)

    if catalyst is None:
        logger.info("No dominant macro catalyst detected — returning empty chain")
        return ContagionChain(
            catalyst="none",
            catalyst_label="No Dominant Catalyst",
            orders=[],
        )

    rules = CONTAGION_RULES.get(catalyst)
    if rules is None:
        logger.warning(f"No contagion rules defined for catalyst: {catalyst}")
        return ContagionChain(
            catalyst=catalyst,
            catalyst_label=_catalyst_label(catalyst),
            orders=[],
        )

    orders = _build_orders(rules)
    impact_labels, impact_scores, impact_colors = _build_impact_chart(rules)

    return ContagionChain(
        catalyst=catalyst,
        catalyst_label=_catalyst_label(catalyst),
        orders=orders,
        impact_labels=impact_labels,
        impact_scores=impact_scores,
        impact_colors=impact_colors,
    )
