"""Expiry analysis: week detection, gap sustain rates, OI distribution, theta."""

from __future__ import annotations

from datetime import datetime, timedelta
from loguru import logger

from config.constants import EXPIRY_DATES_2026, NIFTY_LOT_SIZE
from data.models import OptionsChainData
from features.models import ExpiryAnalysis


def _find_next_expiry(today: datetime) -> tuple[str, int]:
    """Find next expiry date and days remaining.

    Returns (expiry_date_str, days_to_expiry).
    """
    today_str = today.strftime("%Y-%m-%d")

    for exp_str in EXPIRY_DATES_2026:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
        delta = (exp_date - today).days
        if delta >= 0:
            return exp_str, delta

    # If past all 2026 expiries, return last one with 0 days
    return EXPIRY_DATES_2026[-1], 0


def _is_expiry_week(today: datetime, expiry_str: str) -> bool:
    """Check if today falls in the same week as expiry (Mon-Thu of expiry week)."""
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
    # Expiry week = the week containing the expiry date
    # Monday of expiry week
    expiry_weekday = expiry.weekday()  # Thu=3 typically
    monday_of_expiry_week = expiry - timedelta(days=expiry_weekday)
    friday_of_expiry_week = monday_of_expiry_week + timedelta(days=4)
    return monday_of_expiry_week <= today <= friday_of_expiry_week


def _compute_theta_estimate(days_to_expiry: int, vix: float, spot: float) -> float:
    """Estimate daily theta for ATM Nifty option in INR per lot.

    Uses Black-Scholes approximation: theta ≈ -S * sigma / (2 * sqrt(T * 252)) per day.
    Multiply by lot size for per-lot value.
    """
    if days_to_expiry <= 0 or spot <= 0:
        return 0.0

    sigma = vix / 100.0  # VIX is annualized vol in %
    t_years = days_to_expiry / 252.0
    sqrt_t = t_years ** 0.5

    if sqrt_t == 0:
        return 0.0

    # ATM theta per unit per day (approximate)
    daily_theta = spot * sigma / (2 * (252 ** 0.5) * (t_years ** 0.5) * 252)
    theta_per_lot = daily_theta * NIFTY_LOT_SIZE

    return round(theta_per_lot, 0)


def _build_oi_chart_data(options: OptionsChainData, num_strikes: int = 10) -> tuple[list[str], list[float], list[float]]:
    """Extract top OI strikes for the bar chart.

    Returns (strike_labels, call_oi_lakhs, put_oi_lakhs) for the chart.
    """
    if not options.strikes:
        return [], [], []

    spot = options.spot_price
    if spot == 0 and options.strikes:
        spot = options.strikes[len(options.strikes) // 2].strike

    # Get strikes near ATM
    sorted_strikes = sorted(options.strikes, key=lambda s: abs(s.strike - spot))
    near_strikes = sorted_strikes[:num_strikes]
    near_strikes.sort(key=lambda s: s.strike)

    labels = [str(int(s.strike)) for s in near_strikes]
    call_oi = [round(s.call_oi / 100000, 2) for s in near_strikes]  # In lakhs
    put_oi = [round(s.put_oi / 100000, 2) for s in near_strikes]

    return labels, call_oi, put_oi


def compute_expiry_analysis(
    nifty_options: OptionsChainData,
    banknifty_options: OptionsChainData,
    max_pain_nifty: float,
    max_pain_banknifty: float,
    pcr_nifty: float,
    vix: float,
    today: datetime | None = None,
) -> ExpiryAnalysis:
    """Compute expiry-related analytics.

    Parameters
    ----------
    nifty_options : OptionsChainData
    banknifty_options : OptionsChainData
    max_pain_nifty, max_pain_banknifty : float
        From options_analytics module.
    pcr_nifty : float
        Near-ATM PCR.
    vix : float
        India VIX value.
    today : datetime | None
        Override for testing.
    """
    logger.info("Computing expiry analysis")

    if today is None:
        today = datetime.now()

    expiry_str, days_to_expiry = _find_next_expiry(today)
    is_exp_week = _is_expiry_week(today, expiry_str)

    # Gap sustain rate during expiry week is typically lower (pinning effect)
    gap_sustain = 35.0 if is_exp_week else 42.0
    gap_fill_prob = 100.0 - gap_sustain

    # Total premium at stake estimate
    total_premium = 0.0
    for s in nifty_options.strikes:
        total_premium += s.call_ltp * s.call_oi + s.put_ltp * s.put_oi
    total_premium_cr = round(total_premium / 10000000, 0)  # Convert to Crores

    # Theta estimate
    spot = nifty_options.spot_price or 22000.0  # Fallback
    daily_theta = _compute_theta_estimate(days_to_expiry, vix, spot)

    # OI chart data
    oi_strikes, call_oi, put_oi = _build_oi_chart_data(nifty_options)

    return ExpiryAnalysis(
        is_expiry_week=is_exp_week,
        days_to_expiry=days_to_expiry,
        next_expiry_date=expiry_str,
        gap_sustain_rate=gap_sustain,
        gap_fill_probability=gap_fill_prob,
        max_pain_nifty=max_pain_nifty,
        max_pain_banknifty=max_pain_banknifty,
        pcr_nifty=pcr_nifty,
        total_premium_at_stake=total_premium_cr,
        daily_theta_atm=daily_theta,
        oi_strikes=oi_strikes,
        call_oi=call_oi,
        put_oi=put_oi,
    )
