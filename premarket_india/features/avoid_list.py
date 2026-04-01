"""Avoid list: 5-rule engine to flag stocks that should NOT be traded today."""

from __future__ import annotations

from loguru import logger

from data.models import StockOHLCV, OptionsChainData, BlockDeal, NewsItem
from features.models import AvoidFlag


def _check_short_squeeze_risk(stock: StockOHLCV) -> AvoidFlag | None:
    """Rule 1: Short squeeze risk — volume ratio > 3x with delivery < 30%."""
    if stock.volume_ratio > 3.0 and stock.delivery_pct < 30.0:
        return AvoidFlag(
            ticker=stock.ticker,
            reason=f"Volume {stock.volume_ratio:.1f}x avg with only {stock.delivery_pct:.0f}% delivery — possible short squeeze",
            flag_type="Short Squeeze",
            severity="high",
        )
    return None


def _check_iv_crush_risk(
    stock: StockOHLCV,
    options_data: OptionsChainData | None,
) -> AvoidFlag | None:
    """Rule 2: IV crush risk — stock has options with very high IV (results day, etc.)."""
    if options_data is None or not options_data.strikes:
        return None

    # Find ATM strike
    spot = options_data.spot_price
    if spot == 0:
        return None

    atm_strikes = sorted(options_data.strikes, key=lambda s: abs(s.strike - spot))
    if not atm_strikes:
        return None

    atm = atm_strikes[0]
    # Check if IV is extremely high (>50% for equity options is unusual)
    call_iv = atm.call_iv or 0
    put_iv = atm.put_iv or 0
    max_iv = max(call_iv, put_iv)

    if max_iv > 50:
        return AvoidFlag(
            ticker=stock.ticker,
            reason=f"ATM IV at {max_iv:.0f}% — likely binary event; IV crush risk post-event",
            flag_type="IV Crush Risk",
            severity="high",
        )
    return None


def _check_low_liquidity(stock: StockOHLCV) -> AvoidFlag | None:
    """Rule 3: Low liquidity trap — avg volume too low for clean execution."""
    if stock.volume_avg_20d > 0 and stock.volume_avg_20d < 100000:
        return AvoidFlag(
            ticker=stock.ticker,
            reason=f"20d avg volume only {stock.volume_avg_20d:,} — thin liquidity, wide spreads likely",
            flag_type="Low Liquidity",
            severity="high",
        )
    return None


def _check_insider_selling(stock: StockOHLCV, block_deals: list[BlockDeal]) -> AvoidFlag | None:
    """Rule 4: Insider/promoter selling via block deals."""
    relevant = [d for d in block_deals if d.ticker == stock.ticker]
    if not relevant:
        return None

    # If there are block deals and description mentions selling signals
    for deal in relevant:
        desc = (deal.buyer_seller or "").lower()
        if any(kw in desc for kw in ("promoter", "insider", "sell", "offload")):
            return AvoidFlag(
                ticker=stock.ticker,
                reason=f"Block deal detected: {deal.description} — insider selling signal",
                flag_type="Insider Selling",
                severity="critical",
            )
    return None


def _check_binary_event(stock: StockOHLCV, news: list[NewsItem]) -> AvoidFlag | None:
    """Rule 5: Binary event risk — earnings, FDA approval, court ruling, etc."""
    binary_keywords = [
        "earnings", "results", "quarterly", "q4", "q3", "q2", "q1",
        "fda", "court", "verdict", "ruling", "agm", "board meeting",
        "dividend", "split", "bonus", "merger", "acquisition",
    ]
    relevant_news = [n for n in news if stock.ticker in n.tickers]
    for item in relevant_news:
        title_lower = item.title.lower()
        for kw in binary_keywords:
            if kw in title_lower:
                return AvoidFlag(
                    ticker=stock.ticker,
                    reason=f"Binary event: '{item.title}' — unpredictable outcome",
                    flag_type="Binary Event Risk",
                    severity="high",
                )
    return None


def compute_avoid_list(
    stocks: list[StockOHLCV],
    options_data: OptionsChainData | None = None,
    block_deals: list[BlockDeal] | None = None,
    news: list[NewsItem] | None = None,
) -> list[AvoidFlag]:
    """Run all 5 avoidance rules across all stocks.

    Returns list of AvoidFlag for flagged stocks.
    """
    logger.info("Computing avoid list")

    block_deals = block_deals or []
    news = news or []
    flags: list[AvoidFlag] = []

    for stock in stocks:
        # Rule 1: Short squeeze
        flag = _check_short_squeeze_risk(stock)
        if flag:
            flags.append(flag)

        # Rule 2: IV crush (only check if we have options data)
        flag = _check_iv_crush_risk(stock, options_data)
        if flag:
            flags.append(flag)

        # Rule 3: Low liquidity
        flag = _check_low_liquidity(stock)
        if flag:
            flags.append(flag)

        # Rule 4: Insider selling
        flag = _check_insider_selling(stock, block_deals)
        if flag:
            flags.append(flag)

        # Rule 5: Binary event
        flag = _check_binary_event(stock, news)
        if flag:
            flags.append(flag)

    # Sort: critical first, then high
    severity_order = {"critical": 0, "high": 1}
    flags.sort(key=lambda f: severity_order.get(f.severity, 2))

    logger.info(f"Avoid list: {len(flags)} flags across {len(set(f.ticker for f in flags))} stocks")
    return flags
