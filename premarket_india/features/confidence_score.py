"""Confidence score: weighted ensemble of 12 sub-signals → 0-100 mood score."""

from __future__ import annotations

from loguru import logger

from config.constants import CONFIDENCE_WEIGHTS
from data.models import MacroDashboard, FIIDIIData
from features.models import (
    TechnicalLevels,
    OptionsAnalytics,
    GapStatistics,
    SectorFlow,
    SentimentBundle,
    ExpiryAnalysis,
)


def _sgx_signal(macro: MacroDashboard) -> float:
    """SGX Nifty direction signal: -1 (bearish) to +1 (bullish)."""
    pct = macro.sgx_nifty.change_pct
    if pct > 0.5:
        return 1.0
    elif pct > 0.1:
        return 0.5
    elif pct > -0.1:
        return 0.0
    elif pct > -0.5:
        return -0.5
    else:
        return -1.0


def _vix_signal(macro: MacroDashboard) -> float:
    """VIX direction: falling VIX = bullish, rising = bearish."""
    pct = macro.india_vix.change_pct
    if pct < -5:
        return 1.0   # VIX crashing = very bullish
    elif pct < -1:
        return 0.5
    elif pct < 1:
        return 0.0
    elif pct < 5:
        return -0.5
    else:
        return -1.0


def _pcr_signal(options: OptionsAnalytics) -> float:
    """PCR signal: >1.2 = bullish (put writers confident), <0.7 = bearish."""
    pcr = options.pcr_near_atm
    if pcr > 1.5:
        return 1.0
    elif pcr > 1.2:
        return 0.5
    elif pcr > 0.8:
        return 0.0
    elif pcr > 0.7:
        return -0.5
    else:
        return -1.0


def _fii_signal(fii_dii: FIIDIIData) -> float:
    """FII cash flow signal."""
    net = fii_dii.fii_cash_net
    if net > 1000:
        return 1.0
    elif net > 300:
        return 0.5
    elif net > -300:
        return 0.0
    elif net > -1000:
        return -0.5
    else:
        return -1.0


def _dii_signal(fii_dii: FIIDIIData) -> float:
    """DII cash flow signal — strong DII buying when FII sells = supportive."""
    net = fii_dii.dii_cash_net
    if net > 1000:
        return 0.8
    elif net > 300:
        return 0.4
    elif net > -300:
        return 0.0
    elif net > -1000:
        return -0.3
    else:
        return -0.6


def _crude_signal(macro: MacroDashboard) -> float:
    """Crude signal for India: falling crude = bullish for India."""
    pct = macro.brent_crude.change_pct
    if pct < -2:
        return 1.0
    elif pct < -0.5:
        return 0.5
    elif pct < 0.5:
        return 0.0
    elif pct < 2:
        return -0.5
    else:
        return -1.0


def _dow_signal(macro: MacroDashboard) -> float:
    """Dow futures direction signal."""
    pct = macro.dow_futures.change_pct
    if pct > 0.5:
        return 1.0
    elif pct > 0.1:
        return 0.5
    elif pct > -0.1:
        return 0.0
    elif pct > -0.5:
        return -0.5
    else:
        return -1.0


def _sector_breadth_signal(sector_flows: list[SectorFlow]) -> float:
    """Sector breadth: fraction of sectors with positive flow."""
    if not sector_flows:
        return 0.0
    positive = sum(1 for s in sector_flows if s.net_flow > 0)
    ratio = positive / len(sector_flows)
    # Map 0-1 ratio to -1 to +1
    return (ratio - 0.5) * 2.0


def _news_sentiment_signal(sentiment: SentimentBundle) -> float:
    """News sentiment score (-1 to +1) mapped directly."""
    return max(-1.0, min(1.0, sentiment.news_score))


def _social_sentiment_signal(sentiment: SentimentBundle) -> float:
    """Social sentiment score."""
    return max(-1.0, min(1.0, sentiment.overall_score))


def _expiry_adj_signal(expiry: ExpiryAnalysis) -> float:
    """Expiry adjustment: expiry week adds slight bearish bias (pinning/theta decay)."""
    if expiry.is_expiry_week:
        if expiry.days_to_expiry <= 1:
            return -0.5  # Expiry day — very choppy
        return -0.2
    return 0.0


def _rsi_signal(nifty_levels: TechnicalLevels) -> float:
    """RSI signal: oversold = bullish, overbought = bearish."""
    rsi = nifty_levels.rsi
    if rsi < 30:
        return 1.0
    elif rsi < 40:
        return 0.5
    elif rsi < 60:
        return 0.0
    elif rsi < 70:
        return -0.5
    else:
        return -1.0


def compute_confidence_score(
    macro: MacroDashboard,
    fii_dii: FIIDIIData,
    nifty_levels: TechnicalLevels,
    options: OptionsAnalytics,
    gap_stats: GapStatistics,
    sector_flows: list[SectorFlow],
    sentiment: SentimentBundle,
    expiry: ExpiryAnalysis,
) -> int:
    """Compute weighted confidence score from all sub-signals.

    Returns integer 0-100 where:
      0-20  = Very Bearish
      20-40 = Bearish
      40-60 = Neutral
      60-80 = Bullish
      80-100 = Very Bullish
    """
    logger.info("Computing confidence score")

    signals = {
        "sgx_direction": _sgx_signal(macro),
        "vix_direction": _vix_signal(macro),
        "pcr_signal": _pcr_signal(options),
        "fii_flow": _fii_signal(fii_dii),
        "dii_flow": _dii_signal(fii_dii),
        "crude_for_india": _crude_signal(macro),
        "dow_direction": _dow_signal(macro),
        "sector_breadth": _sector_breadth_signal(sector_flows),
        "news_sentiment": _news_sentiment_signal(sentiment),
        "social_sentiment": _social_sentiment_signal(sentiment),
        "expiry_adj": _expiry_adj_signal(expiry),
        "rsi_signal": _rsi_signal(nifty_levels),
    }

    # Weighted sum: each signal is -1 to +1, weight sums to 1.0
    weighted_sum = 0.0
    for key, signal_val in signals.items():
        weight = CONFIDENCE_WEIGHTS.get(key, 0.0)
        weighted_sum += signal_val * weight

    # weighted_sum is in range [-1, +1] → map to [0, 100]
    score = (weighted_sum + 1.0) / 2.0 * 100.0
    score = max(0, min(100, int(round(score))))

    logger.info(f"Confidence score: {score}/100 (raw weighted sum: {weighted_sum:.3f})")
    return score
