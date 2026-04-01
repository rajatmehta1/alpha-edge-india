"""Stock screener: THE MOST IMPORTANT MODULE.

Ranks Nifty 50 stocks by gap-up potential using weighted multi-factor scoring.
Computes entry/target/SL levels for top candidates.
"""

from __future__ import annotations

from loguru import logger

from config.constants import NIFTY_50_STOCKS, SCREENER_WEIGHTS
from data.models import StockOHLCV, MacroDashboard, FIIDIIData
from features.models import GapUpCandidate, PatternMatch, AvoidFlag


def _compute_gap_pct(stock: StockOHLCV, macro: MacroDashboard) -> float:
    """Estimate expected gap % for a stock based on macro move + sector sensitivity."""
    if stock.close == 0:
        return 0.0
    # Use SGX Nifty change as baseline gap estimate
    # Actual stock gap = function of Nifty gap + sector beta
    nifty_gap = macro.sgx_nifty.change_pct
    # Simple heuristic: stock gap ≈ nifty_gap * stock_beta (use weight as proxy)
    info = NIFTY_50_STOCKS.get(stock.ticker, {})
    weight = info.get("weight", 1.0)
    beta_proxy = max(0.5, min(2.0, weight / 3.0))  # Normalize weight to beta-like range
    return round(nifty_gap * beta_proxy, 2)


def _gap_score(gap_pct: float) -> float:
    """Score gap potential: sweet spot is 0.3-1.5% gap up."""
    abs_gap = abs(gap_pct)
    if gap_pct <= 0:
        return 0.0  # No gap-up = no score
    if abs_gap < 0.1:
        return 0.1
    if abs_gap < 0.3:
        return 0.3
    if abs_gap < 0.7:
        return 0.8  # Sweet spot
    if abs_gap < 1.5:
        return 1.0  # Large gap — momentum play
    return 0.6  # Mega gap — higher fill risk


def _catalyst_score(stock: StockOHLCV, fii_dii: FIIDIIData) -> float:
    """Score based on delivery %, volume ratio, and FII flow direction."""
    score = 0.0

    # High delivery % = institutional conviction
    if stock.delivery_pct > 60:
        score += 0.4
    elif stock.delivery_pct > 45:
        score += 0.2

    # Volume ratio > 1.5 = above-average interest
    if stock.volume_ratio > 2.0:
        score += 0.3
    elif stock.volume_ratio > 1.5:
        score += 0.15

    # FII buying direction aligns
    if fii_dii.fii_cash_net > 500:
        score += 0.3
    elif fii_dii.fii_cash_net > 0:
        score += 0.1

    return min(1.0, score)


def _flow_score(stock: StockOHLCV) -> float:
    """Score based on volume and delivery dynamics."""
    score = 0.0

    # Volume ratio
    if stock.volume_ratio > 2.5:
        score += 0.5
    elif stock.volume_ratio > 1.5:
        score += 0.3
    elif stock.volume_ratio > 1.0:
        score += 0.1

    # Delivery %
    if stock.delivery_pct > 55:
        score += 0.5
    elif stock.delivery_pct > 40:
        score += 0.3
    elif stock.delivery_pct > 30:
        score += 0.1

    return min(1.0, score)


def _pattern_score_value(pattern: PatternMatch | None) -> float:
    """Score from pattern matching results."""
    if pattern is None or pattern.total_matches == 0:
        return 0.3  # Neutral when no pattern data

    win_rate = pattern.win_rate or 50.0
    if win_rate > 70:
        return 1.0
    elif win_rate > 60:
        return 0.7
    elif win_rate > 50:
        return 0.4
    else:
        return 0.1


def _volume_score(stock: StockOHLCV) -> float:
    """Score pure volume signal."""
    vr = stock.volume_ratio
    if vr > 3.0:
        return 1.0
    elif vr > 2.0:
        return 0.7
    elif vr > 1.5:
        return 0.5
    elif vr > 1.0:
        return 0.3
    return 0.1


def _avoid_penalty_value(ticker: str, avoid_list: list[AvoidFlag]) -> float:
    """Return penalty if stock is on avoid list."""
    for flag in avoid_list:
        if flag.ticker == ticker:
            if flag.severity == "critical":
                return 1.0  # Full penalty
            return 0.7  # High severity
    return 0.0


def _rsi_penalty_value(rsi: float) -> float:
    """Penalize overbought stocks (RSI > 70)."""
    if rsi > 80:
        return 1.0
    elif rsi > 70:
        return 0.5
    return 0.0


def _compute_levels(
    stock: StockOHLCV,
    gap_pct: float,
    atr_estimate: float,
) -> dict:
    """Compute entry zone, VWAP pullback, targets (T1/T2/T3), and stop loss.

    Parameters
    ----------
    stock : StockOHLCV
    gap_pct : float
        Expected gap %.
    atr_estimate : float
        Estimated ATR for the stock (prev day range * 1.2 as proxy).
    """
    prev_close = stock.close
    if prev_close == 0:
        return {}

    expected_open = prev_close * (1 + gap_pct / 100.0)

    # ATR estimate: use previous day range * 1.2 if we don't have true ATR
    if atr_estimate <= 0:
        day_range = stock.high - stock.low
        atr_estimate = max(day_range * 1.2, prev_close * 0.015)  # Min 1.5% of price

    # Entry zone: between expected open and +0.3% above
    entry_low = round(expected_open, 2)
    entry_high = round(expected_open * 1.003, 2)

    # VWAP pullback: midpoint between prev_close and expected_open
    vwap_pullback = round((prev_close + expected_open) / 2, 2)

    # Targets using ATR multiples
    t1 = round(expected_open + atr_estimate * 0.5, 2)
    t2 = round(expected_open + atr_estimate * 1.0, 2)
    t3 = round(expected_open + atr_estimate * 1.5, 2)

    # Stop loss: below prev_close by 0.5 ATR
    stop_loss = round(prev_close - atr_estimate * 0.3, 2)

    # Risk-reward: (T1 - entry) / (entry - SL)
    risk = entry_low - stop_loss
    reward = t1 - entry_low
    rr = round(reward / risk, 2) if risk > 0 else 0.0

    return {
        "expected_open": expected_open,
        "entry_zone_low": entry_low,
        "entry_zone_high": entry_high,
        "vwap_pullback": vwap_pullback,
        "target_1": t1,
        "target_2": t2,
        "target_3": t3,
        "stop_loss": stop_loss,
        "risk_reward": rr,
    }


def compute_stock_screener(
    stocks: list[StockOHLCV],
    macro: MacroDashboard,
    fii_dii: FIIDIIData,
    avoid_list: list[AvoidFlag],
    pattern_matches: dict[str, PatternMatch] | None = None,
    top_n: int = 3,
) -> list[GapUpCandidate]:
    """Rank Nifty 50 stocks by gap-up potential and return top N candidates.

    Parameters
    ----------
    stocks : list[StockOHLCV]
        All Nifty 50 stock data.
    macro : MacroDashboard
        Macro data for gap estimation.
    fii_dii : FIIDIIData
        FII/DII flow data.
    avoid_list : list[AvoidFlag]
        Stocks to penalize.
    pattern_matches : dict[str, PatternMatch] | None
        Per-stock pattern match results.
    top_n : int
        Number of top candidates to return (default 3).
    """
    logger.info(f"Running stock screener on {len(stocks)} stocks")

    pattern_matches = pattern_matches or {}
    candidates: list[tuple[float, GapUpCandidate]] = []

    w = SCREENER_WEIGHTS

    for stock in stocks:
        info = NIFTY_50_STOCKS.get(stock.ticker, {})
        gap_pct = _compute_gap_pct(stock, macro)

        # Only consider positive gap (gap-up screener)
        if gap_pct <= 0:
            continue

        # Compute sub-scores
        g_score = _gap_score(gap_pct)
        c_score = _catalyst_score(stock, fii_dii)
        f_score = _flow_score(stock)
        p_match = pattern_matches.get(stock.ticker)
        p_score = _pattern_score_value(p_match)
        v_score = _volume_score(stock)
        avoid_pen = _avoid_penalty_value(stock.ticker, avoid_list)

        # RSI penalty — estimate RSI from recent price action
        # (In production this would use the actual RSI from stock history)
        rsi_est = 50.0  # Default if not available
        rsi_pen = _rsi_penalty_value(rsi_est)

        # Weighted composite score
        composite = (
            w["gap_score"] * g_score
            + w["catalyst_score"] * c_score
            + w["flow_score"] * f_score
            + w["pattern_score"] * p_score
            + w["volume_score"] * v_score
            + w["avoid_penalty"] * avoid_pen
            + w["rsi_penalty"] * rsi_pen
        )

        # Compute levels
        atr_est = (stock.high - stock.low) * 1.2 if stock.high > stock.low else stock.close * 0.015
        levels = _compute_levels(stock, gap_pct, atr_est)

        if not levels:
            continue

        candidate = GapUpCandidate(
            rank=0,  # Set after sorting
            ticker=stock.ticker,
            company=info.get("name", stock.name),
            sector=info.get("sector", stock.sector),
            gap_pct=gap_pct,
            expected_open=round(levels["expected_open"], 2),
            prev_close=stock.close,
            entry_zone_low=levels["entry_zone_low"],
            entry_zone_high=levels["entry_zone_high"],
            vwap_pullback=levels["vwap_pullback"],
            target_1=levels["target_1"],
            target_2=levels["target_2"],
            target_3=levels["target_3"],
            stop_loss=levels["stop_loss"],
            risk_reward=levels["risk_reward"],
            options_skew=0.0,  # Filled later if available
            iv_rank=50,
            fii_holding_change=0.0,
            delivery_pct=stock.delivery_pct,
            pattern_match=p_match or PatternMatch(),
        )

        candidates.append((composite, candidate))

    # Sort by composite score descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Take top N and assign ranks
    result: list[GapUpCandidate] = []
    for i, (score, cand) in enumerate(candidates[:top_n]):
        cand.rank = i + 1
        result.append(cand)
        logger.info(f"  #{cand.rank} {cand.ticker}: gap={cand.gap_pct:+.1f}%, score={score:.3f}")

    logger.info(f"Stock screener: {len(result)} candidates selected from {len(candidates)} gap-up stocks")
    return result
