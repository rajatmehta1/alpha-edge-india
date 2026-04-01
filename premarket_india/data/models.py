"""Pydantic models for raw collected data from all 8 collectors."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Macro data points ──

class MacroDataPoint(BaseModel):
    value: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    sparkline: List[float] = Field(default_factory=list)  # Last 10 data points
    source: str = "unknown"
    timestamp: str = ""
    fresh: bool = True
    direction: str = "flat"  # "up", "down", "flat" — controls CSS class


class MacroDashboard(BaseModel):
    sgx_nifty: MacroDataPoint = Field(default_factory=MacroDataPoint)
    dow_futures: MacroDataPoint = Field(default_factory=MacroDataPoint)
    brent_crude: MacroDataPoint = Field(default_factory=MacroDataPoint)
    usdinr: MacroDataPoint = Field(default_factory=MacroDataPoint)
    india_vix: MacroDataPoint = Field(default_factory=MacroDataPoint)
    fii_net: MacroDataPoint = Field(default_factory=MacroDataPoint)
    dii_net: MacroDataPoint = Field(default_factory=MacroDataPoint)
    nifty_prev_close: float = 0.0
    banknifty_prev_close: float = 0.0
    expected_nifty_open: float = 0.0
    expected_banknifty_open: float = 0.0


# ── Stock data ──

class StockOHLCV(BaseModel):
    ticker: str
    name: str = ""
    sector: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    delivery_pct: float = 0.0
    volume_avg_20d: int = 0
    volume_ratio: float = 1.0  # current volume / 20d avg


# ── Options chain ──

class OptionStrike(BaseModel):
    strike: float
    call_oi: int = 0
    put_oi: int = 0
    call_oi_change: int = 0
    put_oi_change: int = 0
    call_volume: int = 0
    put_volume: int = 0
    call_iv: Optional[float] = None
    put_iv: Optional[float] = None
    call_ltp: float = 0.0
    put_ltp: float = 0.0


class OptionsChainData(BaseModel):
    symbol: str
    spot_price: float = 0.0
    strikes: List[OptionStrike] = Field(default_factory=list)
    timestamp: str = ""
    source: str = "nsepython"
    fresh: bool = True


# ── FII/DII ──

class FIIDIIData(BaseModel):
    fii_cash_net: float = 0.0
    dii_cash_net: float = 0.0
    fii_futures_net: float = 0.0
    fii_futures_contracts: int = 0
    fii_options_net: float = 0.0
    fii_options_contracts: int = 0
    fii_5d_total: float = 0.0
    dii_5d_total: float = 0.0
    date: str = ""
    source: str = ""
    fresh: bool = True


class FIIDIIHistory(BaseModel):
    """8-day history for the FII/DII bar chart in Section 13."""
    dates: List[str] = Field(default_factory=list)
    fii_net: List[float] = Field(default_factory=list)
    dii_net: List[float] = Field(default_factory=list)


# ── Block deals ──

class BlockDeal(BaseModel):
    ticker: str
    quantity: int = 0
    price: float = 0.0
    deal_type: str = "Block"  # "Block" or "Bulk"
    buyer_seller: Optional[str] = None
    date: str = ""
    source: str = ""

    @property
    def description(self) -> str:
        if self.buyer_seller:
            return f"{self.buyer_seller} — {self.deal_type.lower()} deal"
        qty_lakhs = self.quantity / 100000
        return f"{self.deal_type} deal: {qty_lakhs:.1f}L shares at \u20b9{self.price:,.0f}"


# ── News ──

class NewsItem(BaseModel):
    title: str
    source: str = ""
    published: str = ""
    url: str = ""
    tickers: List[str] = Field(default_factory=list)
    sentiment_score: float = 0.0  # -1.0 to 1.0


# ── Social sentiment ──

class SentimentData(BaseModel):
    hashtag: str
    ticker: str = ""
    count: int = 0
    bullish: int = 0
    bearish: int = 0
    score: float = 0.0  # -1.0 to 1.0
    source: str = "stocktwits"


# ── TV Analyst calls ──

class TVAnalystCall(BaseModel):
    analyst: str
    channel: str = ""
    stock: str = ""
    direction: str = ""  # "Buy", "Sell", "Short"
    entry_level: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    conflict: Optional[str] = None  # Filled by conflict_agent


# ── Aggregated raw data from all collectors ──

class RawMarketData(BaseModel):
    macro: MacroDashboard = Field(default_factory=MacroDashboard)
    nifty_ohlcv: List[dict] = Field(default_factory=list)  # DataFrame rows as dicts
    banknifty_ohlcv: List[dict] = Field(default_factory=list)
    stock_ohlcv: List[StockOHLCV] = Field(default_factory=list)
    nifty_options: OptionsChainData = Field(default_factory=lambda: OptionsChainData(symbol="NIFTY"))
    banknifty_options: OptionsChainData = Field(default_factory=lambda: OptionsChainData(symbol="BANKNIFTY"))
    fii_dii: FIIDIIData = Field(default_factory=FIIDIIData)
    fii_dii_history: FIIDIIHistory = Field(default_factory=FIIDIIHistory)
    block_deals: List[BlockDeal] = Field(default_factory=list)
    news: List[NewsItem] = Field(default_factory=list)
    social_data: List[SentimentData] = Field(default_factory=list)
    tv_calls: List[TVAnalystCall] = Field(default_factory=list)
    macro_history: List[dict] = Field(default_factory=list)  # For correlation matrix
    stock_history: dict = Field(default_factory=dict)  # ticker -> list of OHLCV dicts
