"""Watchlist queue: template-based time-sequenced intraday alerts."""

from __future__ import annotations

from loguru import logger

from features.models import (
    WatchlistAlert,
    TechnicalLevels,
    GapUpCandidate,
    ExpiryAnalysis,
)


# ── 10 time slots for the trading day ──
_TIME_SLOTS = [
    ("09:00", "critical", "Pre-Open Auction"),
    ("09:15", "critical", "Market Open"),
    ("09:20", "high",     "Gap Assessment"),
    ("09:30", "",         "VWAP Anchor Check"),
    ("10:00", "",         "First Hour Range"),
    ("11:30", "",         "Mid-Morning Review"),
    ("13:00", "",         "Lunch Session"),
    ("14:00", "high",     "Afternoon Momentum"),
    ("15:00", "high",     "Last Hour Setup"),
    ("15:25", "critical", "Close Preparation"),
]


def compute_watchlist_queue(
    nifty_levels: TechnicalLevels,
    gap_up_candidates: list[GapUpCandidate],
    expiry: ExpiryAnalysis,
) -> list[WatchlistAlert]:
    """Generate template-based watchlist alerts for 10 intraday time slots.

    This is NOT LLM-generated — all content is deterministic templates
    with computed levels plugged in.
    """
    logger.info("Computing watchlist queue")

    alerts: list[WatchlistAlert] = []

    # Extract key levels for templates
    pivot = nifty_levels.pivot
    r1 = nifty_levels.r1
    s1 = nifty_levels.s1
    vwap = nifty_levels.vwap
    exp_open = nifty_levels.expected_open
    atr = nifty_levels.atr

    # Top candidate info
    top_stocks = ""
    if gap_up_candidates:
        names = [f"{c.ticker} ({c.gap_pct:+.1f}%)" for c in gap_up_candidates[:3]]
        top_stocks = ", ".join(names)
    else:
        top_stocks = "No gap-up candidates identified"

    expiry_note = ""
    if expiry.is_expiry_week:
        expiry_note = f" [EXPIRY WEEK: {expiry.days_to_expiry}d to expiry]"

    for time, priority, title in _TIME_SLOTS:
        content = _generate_content(
            time, title, pivot, r1, s1, vwap, exp_open, atr,
            top_stocks, expiry_note, gap_up_candidates, expiry,
        )
        alerts.append(WatchlistAlert(
            time=time,
            priority=priority,
            title=title,
            content=content,
        ))

    return alerts


def _generate_content(
    time: str,
    title: str,
    pivot: float,
    r1: float,
    s1: float,
    vwap: float,
    exp_open: float,
    atr: float,
    top_stocks: str,
    expiry_note: str,
    candidates: list[GapUpCandidate],
    expiry: ExpiryAnalysis,
) -> str:
    """Generate content for each time slot based on templates."""

    if time == "09:00":
        return (
            f"Pre-open session begins. Expected Nifty open: {exp_open:,.0f}. "
            f"Watch order book imbalance for direction clue. "
            f"Key stocks: {top_stocks}.{expiry_note}"
        )

    if time == "09:15":
        return (
            f"Market opens. Nifty pivot: {pivot:,.0f} | R1: {r1:,.0f} | S1: {s1:,.0f}. "
            f"If opens above {pivot:,.0f}, bias bullish → watch {r1:,.0f}. "
            f"If below {pivot:,.0f}, watch {s1:,.0f} for support.{expiry_note}"
        )

    if time == "09:20":
        return (
            f"Assess gap direction. If gap sustained above {exp_open:,.0f}, "
            f"wait for first 5-min candle close before entry. "
            f"If gap filling, watch VWAP at {vwap:,.0f} as pullback level."
        )

    if time == "09:30":
        sl_texts = []
        for c in candidates[:2]:
            sl_texts.append(f"{c.ticker}: VWAP pullback ~{c.vwap_pullback:,.0f}, SL {c.stop_loss:,.0f}")
        sl_info = " | ".join(sl_texts) if sl_texts else f"Nifty VWAP: {vwap:,.0f}"
        return f"VWAP anchoring. {sl_info}. No entry below VWAP in gap-up; wait for reclaim."

    if time == "10:00":
        return (
            f"First hour range established. "
            f"Use ATR ({atr:.0f} pts) to set targets: "
            f"T1 = open + {atr * 0.5:.0f} pts, T2 = open + {atr:.0f} pts. "
            f"Breakout above first-hour high = momentum long."
        )

    if time == "11:30":
        return (
            f"Mid-morning check. If Nifty holding above pivot ({pivot:,.0f}), "
            f"trend is intact — trail SL to entry. "
            f"If below pivot, reduce exposure to 50%."
        )

    if time == "13:00":
        return (
            "Lunch session — typically low volume. "
            "Avoid new entries. Review open positions — "
            "tighten stops if in profit, exit losers at VWAP."
        )

    if time == "14:00":
        target_texts = []
        for c in candidates[:2]:
            target_texts.append(f"{c.ticker}: T1={c.target_1:,.0f}, T2={c.target_2:,.0f}")
        t_info = " | ".join(target_texts) if target_texts else f"Nifty R1: {r1:,.0f}"
        return f"Afternoon momentum window. {t_info}. Fresh breakouts often occur 14:00-14:30."

    if time == "15:00":
        if expiry.is_expiry_week and expiry.days_to_expiry <= 1:
            return (
                f"EXPIRY DAY last hour. Max pain Nifty: {expiry.max_pain_nifty:,.0f}. "
                f"Expect pinning toward max pain. Close all option positions by 15:20."
            )
        return (
            f"Last hour. If in profit, book 50% and trail rest. "
            f"If flat, consider cash close — avoid overnight risk. "
            f"Key close level: {pivot:,.0f}."
        )

    if time == "15:25":
        return (
            "Close prep: exit all intraday positions. "
            "Log P&L. Note key levels for tomorrow. "
            "If carrying overnight, ensure stop-loss orders are placed."
        )

    return f"Monitor {title} at {time}."
