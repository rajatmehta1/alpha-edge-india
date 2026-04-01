"""Pydantic models for computed features — output of the feature pipeline."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class TechnicalLevels(BaseModel):
    prev_close: float = 0.0
    expected_open: float = 0.0
    pivot: float = 0.0
    r1: float = 0.0
    r2: float = 0.0
    r3: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    s3: float = 0.0
    vwap: float = 0.0  # VWAP proxy (volume-weighted typical price)
    atr: float = 0.0
    rsi: float = 50.0
    dma_20: float = 0.0
    dma_50: float = 0.0
    dma_200: float = 0.0


class OptionsAnalytics(BaseModel):
    pcr_near_atm: float = 1.0
    pcr_total: float = 1.0
    max_pain_nifty: float = 0.0
    max_pain_banknifty: float = 0.0
    hv_rank: int = 50  # Historical Volatility Rank (proxy for IV Rank)
    skew: float = 0.0  # OTM call IV - OTM put IV
    unusual_activity: List[UnusualOption] = Field(default_factory=list)


class UnusualOption(BaseModel):
    stock: str = ""
    strike: str = ""
    option_type: str = ""  # "Call" or "Put"
    volume: int = 0
    vol_vs_avg: float = 0.0
    oi_change: int = 0
    iv_rank: int = 0
    premium: float = 0.0
    signal: str = ""  # "Bullish", "Bearish", "Hedging"
    ai_score: int = 0


class GapStatistics(BaseModel):
    expected_gap_pct: float = 0.0
    gap_category: str = ""  # "Small", "Medium", "Large", "Mega"
    fill_rate: float = 0.0  # Historical fill rate for this category
    sustain_rate: float = 0.0
    expiry_adjustment: float = 1.0
    vix_regime: str = "medium"  # "low", "medium", "high"
    final_sustain_prob: float = 0.5
    # Per-category stats for the chart
    size_labels: List[str] = Field(default_factory=list)
    sustain_rates: List[float] = Field(default_factory=list)
    fill_rates: List[float] = Field(default_factory=list)
    # Expiry doughnut
    gap_sustained_pct: float = 42.0
    partial_fill_pct: float = 36.0
    full_fill_pct: float = 22.0


class SectorFlow(BaseModel):
    name: str
    emoji: str = ""
    net_flow: float = 0.0  # in Crores
    bar_width: str = "50%"  # CSS width percentage
    color: str = "var(--phosphor)"
    flow_text: str = ""  # "+₹840Cr" or "−₹740Cr"


class CorrelationAnomaly(BaseModel):
    asset_pair: str = ""
    current_corr: float = 0.0
    historical_mean: float = 0.0
    z_score: float = 0.0
    direction: str = ""
    interpretation: str = ""


class CorrelationMatrix(BaseModel):
    assets: List[str] = Field(default_factory=list)
    matrix: List[List[float]] = Field(default_factory=list)
    anomalies: List[CorrelationAnomaly] = Field(default_factory=list)


class SentimentBundle(BaseModel):
    overall_score: float = 0.0  # -1.0 to 1.0
    social_items: List[dict] = Field(default_factory=list)
    news_score: float = 0.0


class PatternMatch(BaseModel):
    total_matches: int = 0
    win_rate: Optional[float] = None
    median_upside: Optional[float] = None
    median_drawdown: Optional[float] = None
    confidence: str = "medium"  # "low", "medium", "high"
    message: str = ""
    detail_text: str = ""


class GapUpCandidate(BaseModel):
    rank: int = 0
    ticker: str = ""
    company: str = ""
    sector: str = ""
    gap_pct: float = 0.0
    expected_open: float = 0.0
    prev_close: float = 0.0
    # Computed levels
    entry_zone_low: float = 0.0
    entry_zone_high: float = 0.0
    vwap_pullback: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    stop_loss: float = 0.0
    risk_reward: float = 0.0
    # Flow data
    options_skew: float = 0.0
    iv_rank: int = 50
    fii_holding_change: float = 0.0
    delivery_pct: float = 0.0
    # Pattern match
    pattern_match: PatternMatch = Field(default_factory=PatternMatch)
    # AI-generated (from stock_analyst_agent)
    catalyst_text: str = ""
    timing_text: str = ""
    ai_score: int = 0


class AvoidFlag(BaseModel):
    ticker: str = ""
    reason: str = ""
    flag_type: str = ""  # "Short Squeeze", "IV Crush Risk", etc.
    severity: str = "high"  # "high", "critical"


class ContagionOrder(BaseModel):
    label: str = ""
    color: str = "var(--phosphor)"
    items: List[ContagionItem] = Field(default_factory=list)


class ContagionItem(BaseModel):
    emoji: str = ""
    name: str = ""
    description: str = ""
    impact_color: str = "var(--phosphor)"  # green/red/amber


class ContagionChain(BaseModel):
    catalyst: str = ""
    catalyst_label: str = ""
    orders: List[ContagionOrder] = Field(default_factory=list)
    impact_labels: List[str] = Field(default_factory=list)
    impact_scores: List[float] = Field(default_factory=list)
    impact_colors: List[str] = Field(default_factory=list)


class ExpiryAnalysis(BaseModel):
    is_expiry_week: bool = False
    days_to_expiry: int = 0
    next_expiry_date: str = ""
    gap_sustain_rate: float = 42.0
    gap_fill_probability: float = 58.0
    max_pain_nifty: float = 0.0
    max_pain_banknifty: float = 0.0
    pcr_nifty: float = 1.0
    total_premium_at_stake: float = 0.0  # in Crores
    daily_theta_atm: float = 0.0  # in INR per lot
    # OI by strike for chart
    oi_strikes: List[str] = Field(default_factory=list)
    call_oi: List[float] = Field(default_factory=list)  # OI in lakhs per strike
    put_oi: List[float] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    day: str = ""  # "MON", "TUE", etc.
    time: str = ""
    title: str = ""
    description: str = ""
    severity: str = ""  # "hi", "med", ""


class WatchlistAlert(BaseModel):
    time: str = ""
    priority: str = ""  # "critical", "high", ""
    title: str = ""
    content: str = ""


class RiskSizing(BaseModel):
    max_risk_per_trade: float = 0.0
    max_risk_text: str = ""
    nifty_atr: float = 0.0
    nifty_atr_text: str = ""
    recommended_lots: int = 1
    recommended_lots_text: str = ""
    expiry_adj_factor: float = 1.0
    expiry_adj_text: str = ""


class ReportMetadata(BaseModel):
    signal_count: int = 0
    pattern_match_count: int = 0
    contagion_chain_count: int = 0
    correlation_anomalies: int = 0
    pipeline_duration: float = 0.0
    generated_at: str = ""
    sections_ok: int = 17
    sections_degraded: int = 0


class SectionStatus:
    """Tracks which sections have complete data vs degraded."""

    def __init__(self):
        self._status: dict[str, str] = {}

    def mark_ok(self, section: str):
        self._status[section] = "ok"

    def mark_degraded(self, section: str, reason: str):
        self._status[section] = f"degraded: {reason}"

    def is_ok(self, section: str) -> bool:
        return self._status.get(section) == "ok"

    def get_message(self, section: str) -> Optional[str]:
        status = self._status.get(section, "ok")
        if status == "ok":
            return None
        return status.replace("degraded: ", "")


# ── Master computed features model ──

class ComputedFeatures(BaseModel):
    macro: "MacroDashboard" = None  # type: ignore[assignment]
    nifty_levels: TechnicalLevels = Field(default_factory=TechnicalLevels)
    banknifty_levels: TechnicalLevels = Field(default_factory=TechnicalLevels)
    options: OptionsAnalytics = Field(default_factory=OptionsAnalytics)
    gap_stats: GapStatistics = Field(default_factory=GapStatistics)
    sector_flows: List[SectorFlow] = Field(default_factory=list)
    correlations: CorrelationMatrix = Field(default_factory=CorrelationMatrix)
    sentiment: SentimentBundle = Field(default_factory=SentimentBundle)
    risk: RiskSizing = Field(default_factory=RiskSizing)
    confidence_score: int = 50
    gap_up_candidates: List[GapUpCandidate] = Field(default_factory=list)
    avoid_list: List[AvoidFlag] = Field(default_factory=list)
    block_deals: List["BlockDeal"] = Field(default_factory=list)  # type: ignore[name-defined]
    pattern_matches: List[PatternMatch] = Field(default_factory=list)
    expiry: ExpiryAnalysis = Field(default_factory=ExpiryAnalysis)
    events_calendar: List[CalendarEvent] = Field(default_factory=list)
    tv_analyst_calls: List["TVAnalystCall"] = Field(default_factory=list)  # type: ignore[name-defined]
    fii_dii_history: "FIIDIIHistory" = None  # type: ignore[assignment]
    contagion_chain: ContagionChain = Field(default_factory=ContagionChain)
    watchlist_alerts: List[WatchlistAlert] = Field(default_factory=list)
    metadata: ReportMetadata = Field(default_factory=ReportMetadata)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def _rebuild(cls):
        """Rebuild forward refs. Call after importing data.models."""
        from data.models import MacroDashboard, BlockDeal, TVAnalystCall, FIIDIIHistory  # noqa: F811
        cls.model_rebuild()


# Trigger rebuild on import
try:
    ComputedFeatures._rebuild()
except Exception:
    pass  # Will be rebuilt when data.models is available
