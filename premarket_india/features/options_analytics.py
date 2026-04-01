"""Options analytics: max pain, PCR, HV rank, skew, unusual OI detection."""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from data.models import OptionsChainData, OptionStrike
from features.models import OptionsAnalytics, UnusualOption


# ---------------------------------------------------------------------------
# Max pain
# ---------------------------------------------------------------------------

def _compute_max_pain(options: OptionsChainData) -> float:
    """Max pain = strike where total writer payout is MINIMUM.

    For each candidate strike P:
        payout = sum over all strikes K of:
            max(0, P - K) * call_oi_at_K  +  max(0, K - P) * put_oi_at_K
    The P with minimum total payout is max pain.
    """
    strikes = options.strikes
    if not strikes:
        return 0.0

    strike_prices = [s.strike for s in strikes]
    call_ois = [s.call_oi for s in strikes]
    put_ois = [s.put_oi for s in strikes]

    min_payout = float("inf")
    max_pain_strike = strike_prices[0] if strike_prices else 0.0

    for p in strike_prices:
        total_payout = 0.0
        for i, k in enumerate(strike_prices):
            call_pain = max(0.0, p - k) * call_ois[i]
            put_pain = max(0.0, k - p) * put_ois[i]
            total_payout += call_pain + put_pain
        if total_payout < min_payout:
            min_payout = total_payout
            max_pain_strike = p

    return float(max_pain_strike)


# ---------------------------------------------------------------------------
# PCR
# ---------------------------------------------------------------------------

def _compute_pcr(strikes: list[OptionStrike], spot: float, atm_range: int = 5) -> tuple[float, float]:
    """Compute near-ATM PCR (±atm_range strikes) and total PCR.

    Returns (pcr_near_atm, pcr_total).
    """
    if not strikes:
        return 1.0, 1.0

    total_call_oi = sum(s.call_oi for s in strikes)
    total_put_oi = sum(s.put_oi for s in strikes)
    pcr_total = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

    # Sort by distance from spot to find nearest strikes
    sorted_strikes = sorted(strikes, key=lambda s: abs(s.strike - spot))
    near_atm = sorted_strikes[:atm_range * 2 + 1]  # ±atm_range around ATM
    near_call = sum(s.call_oi for s in near_atm)
    near_put = sum(s.put_oi for s in near_atm)
    pcr_near = near_put / near_call if near_call > 0 else 1.0

    return round(pcr_near, 3), round(pcr_total, 3)


# ---------------------------------------------------------------------------
# HV Rank (proxy for IV Rank)
# ---------------------------------------------------------------------------

def _compute_hv_rank(close_prices: list[float], short_window: int = 20, long_window: int = 252) -> int:
    """Historical Volatility Rank: percentile of current 20-day HV within 252-day range.

    Returns 0-100 integer.
    """
    if len(close_prices) < short_window + 1:
        return 50

    s = pd.Series(close_prices)
    log_returns = np.log(s / s.shift(1)).dropna()

    if len(log_returns) < short_window:
        return 50

    rolling_hv = log_returns.rolling(window=short_window).std() * np.sqrt(252)
    rolling_hv = rolling_hv.dropna()

    if len(rolling_hv) < 2:
        return 50

    # Use up to long_window of HV values
    lookback = rolling_hv.tail(long_window)
    current_hv = rolling_hv.iloc[-1]

    if current_hv == 0 or lookback.std() == 0:
        return 50

    rank_pct = (lookback < current_hv).sum() / len(lookback) * 100
    return int(round(rank_pct))


# ---------------------------------------------------------------------------
# Options skew
# ---------------------------------------------------------------------------

def _compute_skew(strikes: list[OptionStrike], spot: float, otm_pct: float = 0.03) -> float:
    """Simplified skew: avg OTM call IV - avg OTM put IV.

    OTM calls: strikes > spot * (1 + otm_pct)
    OTM puts:  strikes < spot * (1 - otm_pct)
    Positive skew = call premium > put premium (bearish hedging).
    """
    if not strikes or spot == 0:
        return 0.0

    call_threshold = spot * (1 + otm_pct)
    put_threshold = spot * (1 - otm_pct)

    otm_call_ivs = [s.call_iv for s in strikes if s.strike > call_threshold and s.call_iv is not None and s.call_iv > 0]
    otm_put_ivs = [s.put_iv for s in strikes if s.strike < put_threshold and s.put_iv is not None and s.put_iv > 0]

    avg_call_iv = np.mean(otm_call_ivs) if otm_call_ivs else 0.0
    avg_put_iv = np.mean(otm_put_ivs) if otm_put_ivs else 0.0

    return round(float(avg_call_iv - avg_put_iv), 4)


# ---------------------------------------------------------------------------
# Unusual OI detection
# ---------------------------------------------------------------------------

def _detect_unusual_oi(options: OptionsChainData) -> list[UnusualOption]:
    """Detect strikes where volume > 3x average volume across the chain."""
    strikes = options.strikes
    if not strikes:
        return []

    results: list[UnusualOption] = []

    call_volumes = [s.call_volume for s in strikes if s.call_volume > 0]
    put_volumes = [s.put_volume for s in strikes if s.put_volume > 0]
    avg_call_vol = np.mean(call_volumes) if call_volumes else 0
    avg_put_vol = np.mean(put_volumes) if put_volumes else 0

    for s in strikes:
        # Check calls
        if avg_call_vol > 0 and s.call_volume > 3 * avg_call_vol:
            signal = "Bearish" if s.strike > options.spot_price else "Bullish"
            results.append(UnusualOption(
                stock=options.symbol,
                strike=str(int(s.strike)),
                option_type="Call",
                volume=s.call_volume,
                vol_vs_avg=round(s.call_volume / avg_call_vol, 1),
                oi_change=s.call_oi_change,
                premium=s.call_ltp,
                signal=signal,
                ai_score=0,
            ))
        # Check puts
        if avg_put_vol > 0 and s.put_volume > 3 * avg_put_vol:
            signal = "Bullish" if s.strike < options.spot_price else "Bearish"
            results.append(UnusualOption(
                stock=options.symbol,
                strike=str(int(s.strike)),
                option_type="Put",
                volume=s.put_volume,
                vol_vs_avg=round(s.put_volume / avg_put_vol, 1),
                oi_change=s.put_oi_change,
                premium=s.put_ltp,
                signal=signal,
                ai_score=0,
            ))

    # Sort by vol_vs_avg descending, take top 5
    results.sort(key=lambda x: x.vol_vs_avg, reverse=True)
    return results[:5]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_options_analytics(
    nifty_options: OptionsChainData,
    banknifty_options: OptionsChainData,
    nifty_close_prices: list[float],
) -> OptionsAnalytics:
    """Compute all options analytics from chain data.

    Parameters
    ----------
    nifty_options : OptionsChainData
    banknifty_options : OptionsChainData
    nifty_close_prices : list[float]
        Historical Nifty close prices for HV rank (252+ entries ideal).
    """
    logger.info("Computing options analytics")

    max_pain_nifty = _compute_max_pain(nifty_options)
    max_pain_banknifty = _compute_max_pain(banknifty_options)

    pcr_near, pcr_total = _compute_pcr(
        nifty_options.strikes, nifty_options.spot_price, atm_range=5
    )

    hv_rank = _compute_hv_rank(nifty_close_prices)

    skew = _compute_skew(nifty_options.strikes, nifty_options.spot_price)

    unusual = _detect_unusual_oi(nifty_options) + _detect_unusual_oi(banknifty_options)
    unusual.sort(key=lambda x: x.vol_vs_avg, reverse=True)
    unusual = unusual[:5]

    return OptionsAnalytics(
        pcr_near_atm=pcr_near,
        pcr_total=pcr_total,
        max_pain_nifty=max_pain_nifty,
        max_pain_banknifty=max_pain_banknifty,
        hv_rank=hv_rank,
        skew=skew,
        unusual_activity=unusual,
    )
