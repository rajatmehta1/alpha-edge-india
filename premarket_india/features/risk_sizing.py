"""Risk sizing: position sizing based on capital, VIX, ATR, and expiry."""

from __future__ import annotations

import math
from loguru import logger

from config.constants import NIFTY_LOT_SIZE
from config.settings import settings
from features.models import RiskSizing, ExpiryAnalysis, TechnicalLevels


def compute_risk_sizing(
    nifty_levels: TechnicalLevels,
    expiry: ExpiryAnalysis,
    vix: float,
    capital: int | None = None,
    max_risk_pct: float | None = None,
) -> RiskSizing:
    """Compute position sizing for Nifty futures/options.

    Formula:
      risk_per_trade = capital * max_risk_pct / 100
      risk_per_lot = ATR * lot_size * 0.5
      lots = floor(risk_per_trade / risk_per_lot), min 1
      Apply expiry adjustment factor.

    Parameters
    ----------
    nifty_levels : TechnicalLevels
        Contains ATR.
    expiry : ExpiryAnalysis
        For expiry week adjustment.
    vix : float
        India VIX for additional volatility scaling.
    capital : int | None
        Trading capital; defaults to settings.TRADING_CAPITAL.
    max_risk_pct : float | None
        Max risk per trade %; defaults to settings.MAX_RISK_PER_TRADE_PCT.
    """
    logger.info("Computing risk sizing")

    capital = capital or settings.TRADING_CAPITAL
    max_risk_pct = max_risk_pct or settings.MAX_RISK_PER_TRADE_PCT

    atr = nifty_levels.atr
    if atr <= 0:
        atr = 200.0  # Fallback ~200 points for Nifty
        logger.warning("ATR is 0, using fallback of 200")

    # Risk per trade in INR
    risk_per_trade = capital * max_risk_pct / 100.0

    # Risk per lot: half ATR as stop distance * lot size
    risk_per_lot = atr * NIFTY_LOT_SIZE * 0.5

    if risk_per_lot <= 0:
        risk_per_lot = 1.0  # Safety

    # Raw lot count
    raw_lots = risk_per_trade / risk_per_lot

    # VIX adjustment: reduce size if VIX is elevated
    vix_factor = 1.0
    if vix > 20:
        vix_factor = 0.75
    elif vix > 25:
        vix_factor = 0.5

    # Expiry adjustment: reduce near expiry (gamma risk)
    expiry_factor = 1.0
    if expiry.is_expiry_week:
        if expiry.days_to_expiry <= 1:
            expiry_factor = 0.50  # Expiry day — halve position
        elif expiry.days_to_expiry <= 2:
            expiry_factor = 0.75
        else:
            expiry_factor = 0.90

    adjusted_lots = raw_lots * vix_factor * expiry_factor
    lots = max(1, math.floor(adjusted_lots))

    # Build text descriptions
    risk_text = f"₹{risk_per_trade:,.0f} ({max_risk_pct:.1f}% of ₹{capital / 100000:.0f}L)"
    atr_text = f"{atr:.0f} pts (SL @ {atr * 0.5:.0f} pts)"
    lots_text = f"{lots} lot{'s' if lots > 1 else ''} ({lots * NIFTY_LOT_SIZE} units)"

    expiry_parts = []
    if vix_factor < 1.0:
        expiry_parts.append(f"VIX adj ×{vix_factor:.2f}")
    if expiry_factor < 1.0:
        expiry_parts.append(f"Expiry adj ×{expiry_factor:.2f}")
    expiry_adj_text = ", ".join(expiry_parts) if expiry_parts else "No adjustment"

    return RiskSizing(
        max_risk_per_trade=risk_per_trade,
        max_risk_text=risk_text,
        nifty_atr=atr,
        nifty_atr_text=atr_text,
        recommended_lots=lots,
        recommended_lots_text=lots_text,
        expiry_adj_factor=round(vix_factor * expiry_factor, 2),
        expiry_adj_text=expiry_adj_text,
    )
