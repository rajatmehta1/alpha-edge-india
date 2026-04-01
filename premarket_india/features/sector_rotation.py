"""Sector rotation scoring from stock data and FII/DII flows."""

from __future__ import annotations

from loguru import logger

from config.constants import NIFTY_50_STOCKS, SECTORS, SECTOR_SENSITIVITY
from data.models import StockOHLCV, FIIDIIData
from features.models import SectorFlow


_SECTOR_EMOJIS = {
    "Banking": "🏦", "IT": "💻", "Oil & Gas": "⛽", "Auto": "🚗",
    "Pharma": "💊", "FMCG": "🧴", "Metals": "⚙", "Paints": "🎨",
    "Aviation": "✈", "Retail": "🛍", "Telecom": "📡", "Infra": "🏗",
    "Power": "⚡", "Cement": "🏢", "NBFC": "💰", "Consumer": "🛒",
    "Insurance": "🛡", "Conglomerate": "🏭",
}


def compute_sector_rotation(
    stocks: list[StockOHLCV],
    fii_dii: FIIDIIData,
    crude_change_pct: float = 0.0,
    usdinr_change_pct: float = 0.0,
) -> list[SectorFlow]:
    """Score sectors by combining stock-level signals with macro sensitivity.

    Scoring:
      1. Aggregate stock performance per sector (volume-weighted avg delivery_pct * volume_ratio).
      2. Apply macro sensitivity adjustments (crude, forex).
      3. Add FII/DII tilt (FII positive = overweight Banking/IT, negative = defensive tilt).

    Returns sorted list of SectorFlow (descending by net_flow).
    """
    logger.info("Computing sector rotation")

    # Build sector → stocks mapping
    sector_stocks: dict[str, list[StockOHLCV]] = {s: [] for s in SECTORS}
    for stock in stocks:
        sect = stock.sector
        if sect in sector_stocks:
            sector_stocks[sect].append(stock)

    # Step 1: aggregate stock-level activity score per sector
    sector_scores: dict[str, float] = {}
    for sector, stk_list in sector_stocks.items():
        if not stk_list:
            sector_scores[sector] = 0.0
            continue
        total_score = 0.0
        for s in stk_list:
            # Higher delivery % + higher volume ratio = stronger institutional interest
            activity = s.delivery_pct * s.volume_ratio
            total_score += activity
        sector_scores[sector] = total_score / len(stk_list)

    # Step 2: macro sensitivity adjustment
    for sector in SECTORS:
        sens = SECTOR_SENSITIVITY.get(sector, {})
        crude_adj = sens.get("crude", 0) * crude_change_pct * 0.1
        fx_adj = sens.get("usdinr", 0) * usdinr_change_pct * 0.1
        sector_scores[sector] = sector_scores.get(sector, 0) + crude_adj + fx_adj

    # Step 3: FII/DII tilt
    fii_net = fii_dii.fii_cash_net
    if fii_net > 500:  # Strong FII buying (>500 Cr)
        for s in ("Banking", "IT"):
            sector_scores[s] = sector_scores.get(s, 0) + 0.5
    elif fii_net < -500:  # Strong FII selling
        for s in ("FMCG", "Pharma"):
            sector_scores[s] = sector_scores.get(s, 0) + 0.3

    # Normalize to approximate crore-like flow values for display
    max_score = max(abs(v) for v in sector_scores.values()) if sector_scores else 1.0
    if max_score == 0:
        max_score = 1.0

    flows: list[SectorFlow] = []
    for sector in SECTORS:
        raw = sector_scores.get(sector, 0.0)
        # Scale to a display-friendly range (±1000 Cr)
        scaled_flow = round((raw / max_score) * 1000, 0)
        bar_pct = max(5, min(100, int(abs(raw) / max_score * 100)))
        color = "var(--phosphor)" if scaled_flow >= 0 else "var(--red)"
        sign = "+" if scaled_flow >= 0 else "−"

        flows.append(SectorFlow(
            name=sector,
            emoji=_SECTOR_EMOJIS.get(sector, "📊"),
            net_flow=scaled_flow,
            bar_width=f"{bar_pct}%",
            color=color,
            flow_text=f"{sign}₹{abs(scaled_flow):.0f}Cr",
        ))

    flows.sort(key=lambda f: f.net_flow, reverse=True)
    return flows
