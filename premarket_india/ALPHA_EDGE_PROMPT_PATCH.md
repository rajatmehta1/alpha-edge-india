# ALPHA EDGE — Prompt Audit & Patch
## Critical fixes to ensure output matches alpha-edge-v2.html exactly

---

> **INSTRUCTIONS FOR CLAUDE CODE**: This patch document supplements the main 
> `ALPHA_EDGE_CLAUDE_CODE_PROMPT.md`. Apply ALL changes below BEFORE building. 
> These fix 12 critical gaps that would cause the generated report to NOT 
> match the reference design. Read this ENTIRE document first, then build.

---

## AUDIT SUMMARY: 12 Critical Gaps Found

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| 1 | 4 missing feature modules | Sections 11,12,15,16 would be empty | Add avoid_list.py, expiry_analysis.py, watchlist_queue.py, events_calendar.py |
| 2 | No stock screening/ranking algorithm | Section 03 can't pick top 3 stocks | Add stock_screener.py with scoring formula |
| 3 | No stock entry/target/SL computation | Section 03 key levels would be empty | Add level computation logic to stock_screener.py |
| 4 | No TV analyst data source | Section 10 TV panel would be empty | Add tv_analysts.py collector with curated + AI generation |
| 5 | Missing 6th agent for watchlist | Section 15 requires LLM-generated time-based alerts | Add watchlist_agent.py to the LangGraph graph |
| 6 | Incomplete ComputedFeatures model | Template would have missing variables | Add 8 missing fields to the model |
| 7 | No chart configuration spec | 12 Chart.js charts would render wrong | Add exact chart specs for all 12 canvases |
| 8 | Incomplete Jinja2 variable mapping | Template can't render all 17 sections | Add complete variable map for every section |
| 9 | No reference HTML embedding instruction | Claude Code won't know the exact CSS | Add explicit file embedding step |
| 10 | No report filename convention | Files would have random names | Specify: alpha_edge_YYYY-MM-DD.html |
| 11 | Sparkline data not in ComputedFeatures | Hero mood cards would have no sparklines | Add sparkline arrays to MacroDashboard model |
| 12 | Correlation matrix not in template spec | Section 07 would be empty | Add JS-based heatmap generation spec |

---

## FIX 1: Add 4 Missing Feature Modules

### Add to directory structure:
```
features/
├── ...existing files...
├── stock_screener.py         # NEW — Gap-up candidate identification + ranking + levels
├── avoid_list.py             # NEW — Stock avoidance rules engine
├── expiry_analysis.py        # NEW — Expiry week stats, OI distribution, theta
├── watchlist_queue.py        # NEW — Time-sequenced intraday alert generation
└── events_calendar.py        # NEW — Weekly events calendar data
```

### `features/stock_screener.py` — Gap-Up Candidate Identification & Ranking
```
This is the MOST IMPORTANT missing module. It answers: "Which 3 stocks appear 
in the Top Gap-Up Setups section, and what are their entry/target/SL levels?"

INPUT: All Nifty 50 stock OHLCV, sector flows, crude/macro changes, options data
OUTPUT: List[GapUpCandidate] ranked by AI score (top 3 shown in report)

RANKING ALGORITHM (weighted scoring):
  gap_score = normalize(expected_gap_pct) * 0.25        # Bigger gap = more potential
  catalyst_score = sector_tailwind_strength * 0.20       # Sector benefiting from macro?
  flow_score = (options_skew + delivery_pct) * 0.15      # Smart money confirmation
  pattern_score = historical_win_rate * 0.15             # Pattern engine confidence
  volume_score = normalize(volume_ratio) * 0.10          # Above-avg volume = conviction
  avoid_penalty = -0.5 if in_avoid_list else 0           # Penalize flagged stocks
  rsi_penalty = -0.15 if rsi > 72 else 0                 # Overbought penalty
  
  total_score = sum of above, normalized to 0-100

LEVEL COMPUTATION (for each top-3 stock):
  prev_close = stock.close
  expected_open = prev_close * (1 + expected_gap_pct)
  
  # Entry zone: between expected open and VWAP
  entry_low = min(expected_open, vwap) 
  entry_high = expected_open * 1.005  # Slight premium above open
  
  # VWAP pullback target = previous session VWAP
  vwap_pullback = stock.vwap
  
  # Targets using ATR:
  atr = stock.atr_14
  target_1 = expected_open + (atr * 0.5)     # Conservative: 0.5× ATR
  target_2 = expected_open + (atr * 1.0)     # Moderate: 1.0× ATR
  target_3 = expected_open + (atr * 1.5)     # Aggressive: 1.5× ATR
  
  # Stop loss: below gap fill level
  stop_loss = prev_close * 0.998  # Just below previous close (gap fill = loss)
  
  # Risk/Reward ratio
  risk = entry_high - stop_loss
  reward = target_2 - entry_high
  risk_reward = reward / risk

SECTOR SENSITIVITY MAP (for expected gap calculation):
  Aviation: crude_sensitivity = -1.8   (crude down = strong positive)
  Paints: crude_sensitivity = -1.2
  Auto/Tyres: crude_sensitivity = -0.8
  FMCG: crude_sensitivity = -0.4
  Oil & Gas (OMC): crude_sensitivity = +1.5  (crude down = negative)
  Oil & Gas (Upstream): crude_sensitivity = +1.0
  IT: usdinr_sensitivity = -1.2  (INR strengthen = negative)
  Banking: rate_sensitivity = +0.8  (rate cut hopes = positive)
```

### `features/avoid_list.py` — Stock Avoidance Rules Engine
```
INPUT: All stock data, options analytics, block deals, news
OUTPUT: List[AvoidFlag] with ticker, reason, flag_type

RULES (check each, flag if triggered):

1. SHORT SQUEEZE RISK:
   if stock.change_5d < -5% AND futures_short_oi > percentile_90:
     flag("Short Squeeze", "Already down {x}% in 5 sessions, short OI at 
     {n}-month high. {pct}% of gap-downs after extended decline see bounce.")

2. IV CRUSH RISK:
   if stock.iv_rank > 75 AND stock.days_to_earnings < 5:
     flag("IV Crush Risk", "Results due in {n} days. IV at {iv_rank}th percentile.
     Directional option plays lose {pct}% from IV crush.")

3. LOW LIQUIDITY TRAP:
   if stock.volume_ratio < 0.6 AND stock.delivery_pct < 30:
     flag("Liquidity Trap", "Volume down {x}% over 10 sessions. Delivery {d}%.
     Low vol + gap = false breakout {pct}% of time.")

4. INSIDER SELLING:
   if stock.ticker in block_deal_sellers AND stock in analyst_downgrades:
     flag("Insider Exit", "Block sell at ₹{price}. {n} analyst downgrades. 
     Smart money exiting.")

5. BINARY EVENT RISK:
   if stock.has_pending_legal_event OR stock.has_regulatory_hearing:
     flag("Binary Risk", "Event this week. Options pricing ±{x}% move.
     Legal-event stocks: {pct}% hit rate on directional trades.")

Each flag includes: ticker, flag_type, reason_text (with data-filled template),
severity (high/critical).
```

### `features/expiry_analysis.py` — Expiry Week Statistics
```
INPUT: Options chain data, historical expiry data, gap analysis
OUTPUT: ExpiryAnalysis model

COMPUTE:
  is_expiry_week: bool          # Is this week a monthly expiry week?
  days_to_expiry: int           # Days until monthly expiry
  gap_sustain_rate: float       # Historical: % of expiry Monday gaps that sustained
  gap_fill_probability: float   # 1 - gap_sustain_rate
  max_pain_nifty: float         # From options_analytics
  max_pain_banknifty: float
  pcr_nifty: float              # From options_analytics
  total_premium_at_stake: float # Sum of all Nifty option premiums × OI × lot_size
  daily_theta_atm: float        # ATM option theta in ₹ per lot
  
  # OI by strike data (for the OI chart in section 12):
  oi_strikes: List[str]         # ["23000","23100",..."23900"]
  call_oi: List[float]          # OI in lakhs per strike
  put_oi: List[float]           # OI in lakhs per strike

If not expiry week, still compute but mark is_expiry_week=False.
Template conditionally shows/hides expiry section.
```

### `features/events_calendar.py` — Weekly Events Calendar
```
INPUT: News headlines, earnings calendar, economic calendar
OUTPUT: List[CalendarEvent]

DATA SOURCES:
  1. Earnings calendar: Hardcode known Q4 FY26 results dates for Nifty 50 stocks
     (TCS, Infosys, HDFC Bank, etc. — these are publicly known weeks in advance)
  2. Economic calendar: Scrape from https://www.moneycontrol.com/economic-calendar/
     OR use a hardcoded template for common monthly events:
       - Auto sales data: 1st of every month
       - RBI MPC: scheduled dates
       - US NFP: first Friday of every month
       - F&O expiry: last Thursday
  3. Today's key moments: Always include market open (09:15), pre-market (09:00)

CalendarEvent model:
  day: str            # "MON", "TUE", etc.
  time: str           # "09:00", "16:00"
  title: str          # "TCS Q4 Results"
  description: str    # "IT bellwether. Consensus: Rev +4.1% QoQ"
  severity: str       # "high", "medium", "low"

For MVP: Use a curated template that gets filled with this week's known events.
The LLM does NOT generate events — they come from data/curated lists.
```

### `features/watchlist_queue.py` — Intraday Alert Schedule
```
INPUT: Top 3 gap-up stocks (with levels), Nifty levels, expiry analysis, risk sizing
OUTPUT: List[WatchlistAlert]

This is a TEMPLATE-BASED generator, NOT LLM-generated:

STATIC TEMPLATE (always the same time slots, content varies):
  09:00 — Pre-market: "Watch order book for {stock1}, {stock2}, {stock3}"
  09:15 — Opening bell: "Mark opening range on Nifty ({open_low}–{open_high})"
  09:20 — VWAP retest: "If {stock1} pulls back to ₹{vwap1} — primary entry"
  09:30 — Pullback window: "If {stock2} holds ₹{vwap2}, enter 50%"
  09:45 — Trend check: "Nifty above VWAP ({nifty_vwap})? → Scenario A. Below → B"
  10:30 — Gap deadline: "If Nifty above {gap_sustain_level} → gap sustained"
  11:30 — Midday: "Book 70% profits if targets not hit"
  14:00 — Danger zone (expiry weeks): "Close short-dated options"
  15:00 — Power hour: "If Nifty above {key_level} → short covering rally"
  15:25 — Close: "Square off everything. No overnight in expiry week."

Each alert has: time, priority (critical/high/normal), content (with filled levels).
```

---

## FIX 2: Add Missing Collector

### `data/collectors/tv_analysts.py` — TV Analyst Calls
```
This data is NOT available via any free API. Three strategies:

STRATEGY 1 (MVP — Curated): 
  Maintain a daily-updated JSON file with recent analyst calls.
  Source: Manually check CNBC-TV18 and ET Now morning shows, or scrape
  from moneycontrol.com/news/tags/stock-recommendations.html

STRATEGY 2 (Semi-automated):
  Use feedparser to scrape RSS from:
    - https://www.moneycontrol.com/rss/buzzingstocks.xml  
    - Search for analyst names in headlines
  Extract: analyst_name, stock, direction (buy/sell), target, stop_loss

STRATEGY 3 (AI-generated for realism):
  When no real data available, use the Conflict Agent to generate 
  REALISTIC analyst calls based on the computed data, then check them
  for conflicts. Mark these as "AI-simulated" in the report.

TVAnalystCall model:
  analyst: str         # "Sudarshan Sukhani"
  channel: str         # "CNBC-TV18"
  stock: str           # "INDIGO"
  direction: str       # "Buy" / "Sell" / "Short"
  entry_level: float   # ₹4,600
  target: float        # ₹4,750
  stop_loss: float     # ₹4,520
  conflict: Optional[str]  # Filled by conflict_agent if contradiction found
```

---

## FIX 3: Add 6th Agent — Watchlist Agent

### Update `agents/graph.py` topology:
```
                    ┌─ narrative_agent ───┐
                    ├─ stock_analyst ─────┤
  computed_data ──→ ├─ options_agent ─────┤ ──→ merge_outputs ──→ ReportPayload
                    ├─ scenario_agent ────┤
                    ├─ conflict_agent ────┤
                    └─ watchlist_agent ───┘   ← NEW (6th agent)
```

### `agents/watchlist_agent.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Watchlist Agent. You create a time-sequenced 
alert schedule for the trading day based on pre-computed stock levels and scenarios.

RULES:
1. Create exactly 10 time-based alerts from 09:00 to 15:25.
2. Each alert must reference SPECIFIC price levels from the data provided.
3. Use the exact stock tickers and ₹ levels — no rounding, no estimating.
4. Mark alerts as "critical" (09:00, 09:15), "high" (entry windows, danger zones), 
   or "normal" (checkpoints).
5. Reference Scenario A/B/C from the scenario playbook in the 09:45 alert.
6. Output as JSON: list of {time, priority, title, content} objects.
"""
```

### Update AgentState in `agents/state.py`:
```python
class AgentState(TypedDict):
    computed_features: ComputedFeatures
    narrative: Optional[NarrativeOutput]
    stock_analyses: Optional[List[StockAnalysis]]
    options_summary: Optional[str]
    scenario_playbook: Optional[ScenarioPlaybook]
    conflict_flags: Optional[List[ConflictFlag]]
    watchlist_alerts: Optional[List[WatchlistAlert]]  # ← NEW
```

---

## FIX 4: Complete ComputedFeatures Model

### Update `features/models.py` — add ALL missing fields:
```python
class ComputedFeatures(BaseModel):
    # ── EXISTING (already in prompt) ──
    macro: MacroDashboard
    nifty_levels: TechnicalLevels
    banknifty_levels: TechnicalLevels
    options: OptionsAnalytics
    gap_stats: GapStatistics
    sector_flows: List[SectorFlow]
    correlations: CorrelationMatrix
    sentiment: SentimentBundle
    risk: RiskSizing
    confidence_score: int
    gap_up_candidates: List[GapUpCandidate]
    avoid_list: List[AvoidFlag]
    block_deals: List[BlockDeal]
    pattern_matches: List[PatternMatch]
    
    # ── NEW — were missing from original prompt ──
    expiry: ExpiryAnalysis              # Section 12 data
    events_calendar: List[CalendarEvent] # Section 16 data
    tv_analyst_calls: List[TVAnalystCall] # Section 10 TV panel data
    fii_dii_history: FIIDIIHistory       # Section 13 chart data (8-day history)
    contagion_chain: ContagionChain       # Section 05 data (was missing from model)

class MacroDashboard(BaseModel):
    # ── EXISTING ──
    sgx_nifty: MacroDataPoint
    dow_futures: MacroDataPoint
    brent_crude: MacroDataPoint
    usdinr: MacroDataPoint
    india_vix: MacroDataPoint
    fii_net: MacroDataPoint
    dii_net: MacroDataPoint       # ← WAS MISSING — needed for masthead pill
    
class MacroDataPoint(BaseModel):
    value: float
    change: float
    change_pct: float
    sparkline: List[float]         # ← WAS MISSING — last 10 data points for sparkline chart
    source: str
    timestamp: str
    fresh: bool
    direction: str                 # "up", "down", "flat" — controls CSS class

class FIIDIIHistory(BaseModel):
    """8-day history for the FII/DII bar chart in Section 13"""
    dates: List[str]               # ["21 Mar", "22 Mar", ...]
    fii_net: List[float]           # [-2100, -1800, ...]
    dii_net: List[float]           # [1800, 2400, ...]

class GapUpCandidate(BaseModel):
    rank: int
    ticker: str
    company: str
    sector: str
    gap_pct: float
    expected_open: float
    prev_close: float
    # Computed levels:
    entry_zone_low: float
    entry_zone_high: float
    vwap_pullback: float
    target_1: float
    target_2: float
    target_3: float
    stop_loss: float
    risk_reward: float
    # Flow data:
    options_skew: float
    iv_rank: int
    fii_holding_change: float      # % change in FII holdings
    delivery_pct: float
    # Pattern match:
    pattern_match: PatternMatch
    # AI-generated (from stock_analyst_agent):
    catalyst_text: str             # Filled by AI agent
    timing_text: str               # Filled by AI agent
    ai_score: int                  # 0-100 ranking score
```

---

## FIX 5: Complete Chart.js Configuration Spec

### All 12 charts must match the reference exactly. Add this to the prompt:

```
report/chart_data.py must prepare JSON data for these 12 Chart.js charts:

CHART 1-6: SPARKLINES (sp1 through sp6)
  Type: line
  Config: {
    borderColor: color (green for up, red for down, amber for flat),
    borderWidth: 1.5, pointRadius: 0, fill: true,
    backgroundColor: color + "18" (very transparent),
    tension: 0.4
  }
  Options: { responsive:true, maintainAspectRatio:false, 
    plugins:{legend:{display:false},tooltip:{enabled:false}},
    scales:{x:{display:false},y:{display:false}} }
  Data: 10 data points from MacroDataPoint.sparkline

CHART 7: SECTOR ROTATION (sectorChart)
  Type: bar (horizontal — indexAxis:'y')
  Labels: sector names sorted by flow magnitude
  Data: net flow values (positive = green, negative = red)
  Colors: Per-bar coloring based on positive/negative value
  Config: { borderRadius:4, barPercentage:0.7 }

CHART 8: CONTAGION IMPACT (contagionChart)
  Type: bar (vertical)
  Labels: ["Airlines","Paints","Tyres","FMCG","Logistics","RBI Cut","FII Flow","OMCs","Oil Svcs","Metals"]
  Data: impact scores (positive = green, negative = red)
  Config: { borderRadius:5, barPercentage:0.65 }
  Title: "Crude Oil Drop — Impact Score by Sector & Macro"

CHART 9: GAP SIZE ANALYSIS (gapSizeChart)  
  Type: bar (vertical, grouped)
  Labels: ["<0.3% Small","0.3-0.5% Mod","0.5-1.0% Med","1.0-1.5% Lrg",">1.5% Mega"]
  Datasets: 2 — "Sustain Rate %" and "Gap Fill Rate %"
  Colors: Green gradient for sustain, transparent green for fill
  Y-axis max: 100

CHART 10: GAP EXPIRY DOUGHNUT (gapExpiryChart)
  Type: doughnut
  Labels: ["Gap Sustained","Partial Fill (50%+)","Full Gap Fill"]
  Data: [42, 36, 22]  (or computed values)
  Colors: [green, amber, red] with cc opacity
  Config: { cutout:"55%" }

CHART 11: NIFTY OI BY STRIKE (oiChart)
  Type: bar (vertical, grouped)
  Labels: Strike prices ["23000","23100",...,"23900"]
  Datasets: 2 — "Call OI (Lakh)" (red) and "Put OI (Lakh)" (green)
  Title: "Nifty OI by Strike — Expiry Series"

CHART 12: FII vs DII FLOW (fiiChart)
  Type: bar (vertical, grouped)
  Labels: Last 8 trading dates
  Datasets: 2 — "FII Net" (red) and "DII Net" (green)
  Title: "FII vs DII — Last 8 Sessions"

CRITICAL: All charts must use these exact Phosphor Terminal colors:
  green: '#00E87B'
  red: '#FF4757'
  amber: '#FFB84D'
  blue: '#4DC9F6'
  violet: '#A78BFA'
  gridColor: 'rgba(255,255,255,0.04)'
  textColor: '#5A6580'
  tooltipBg: '#1A2540'
  tooltipBorder: '#253050'
  font: "'IBM Plex Mono', monospace"
  titleFont: "'Instrument Serif'"
```

---

## FIX 6: Complete Jinja2 Template Variable Mapping

### Every section of the template must have explicit variable names. Add this:

```
=== MASTHEAD (Sticky Header) ===
Pills:
  {% for pill in masthead_pills %}
    {{ pill.text }}     # e.g. "SGX Nifty +0.68%"
    {{ pill.class }}    # "pill-green", "pill-red", "pill-amber"
  {% endfor %}
  
Generated time: {{ generated_at }}  # "07:18 IST"
Signal count: {{ signal_count }}    # 847

=== HERO (Macro Dashboard) ===
Date: {{ report_date_long }}        # "Monday, 30 March 2026"

Mood cards — iterate: {% for card in macro_cards %}
  {{ card.label }}                   # "SGX Nifty"
  {{ card.value }}                   # "23,542"
  {{ card.delta }}                   # "▲ +158.4 (+0.68%)"
  {{ card.direction }}               # "mc-up", "mc-down", "mc-flat"
  {{ card.canvas_id }}               # "sp1"
{% endfor %}

Score bar:
  {{ confidence_score }}             # 72
  {{ confidence_label }}             # "Moderately Bullish"
  {{ confidence_color }}             # "var(--phosphor)" or "var(--danger)"

=== S01: MARKET NARRATIVE ===
  {{ narrative.headline }}
  {{ narrative.body | safe }}       # NOTE: use |safe for HTML (line breaks)
  {% for b in narrative.bullets %}
    {{ b.icon }}                     # "M", "F", "R", "E"
    {{ b.text | safe }}
  {% endfor %}

=== S02: TECHNICAL LEVELS ===
Nifty:
  {{ nifty.prev_close }}
  {{ nifty.r3 }} {{ nifty.r2 }} {{ nifty.r1 }}
  {{ nifty.expected_open }}
  {{ nifty.pivot }}
  {{ nifty.vwap }}
  {{ nifty.s1 }} {{ nifty.s2 }} {{ nifty.s3 }}
  {{ nifty.pcr }} {{ nifty.max_pain }} {{ nifty.atr }}
BankNifty: same pattern with {{ banknifty.* }}

=== S03: GAP-UP SETUPS ===
{% for stock in gap_up_stocks[:3] %}  ← ONLY TOP 3
  {{ stock.rank }} {{ stock.ticker }} {{ stock.company }} {{ stock.sector }}
  {{ stock.gap_pct }}
  {{ stock.catalyst_text | safe }}           # From AI agent
  {{ stock.timing_text | safe }}             # From AI agent
  Options: {{ stock.options_skew }} {{ stock.iv_rank }}
  Levels: {{ stock.entry_zone_low }} {{ stock.entry_zone_high }}
          {{ stock.vwap_pullback }}
          {{ stock.target_1 }} {{ stock.target_2 }} {{ stock.target_3 }}
          {{ stock.stop_loss }} {{ stock.risk_reward }}
  Pattern: {{ stock.pattern_match.total_matches }}
           {{ stock.pattern_match.win_rate }}
           {{ stock.pattern_match.median_upside }}
           {{ stock.pattern_match.median_drawdown }}
{% endfor %}

=== S04: SECTOR ROTATION ===
{% for sf in sector_flows %}
  {{ sf.emoji }} {{ sf.name }}
  {{ sf.net_flow }}                  # "+₹840Cr" or "−₹740Cr"
  {{ sf.bar_width }}                 # Percentage for CSS width (e.g. "92%")
  {{ sf.color }}                     # "var(--phosphor)" or "var(--danger)"
{% endfor %}
Chart data: {{ sector_chart_data | tojson }}

=== S05: CONTAGION CHAIN ===
{{ contagion_chart_data | tojson }}
{% for order in contagion.orders %}
  {{ order.label }}                   # "1st Order — Direct Impact"
  {{ order.color }}                   # "var(--phosphor)"
  {% for item in order.items %}
    {{ item.emoji }} {{ item.name }}
    {{ item.description }}
    {{ item.impact_color }}           # green/red/amber
  {% endfor %}
{% endfor %}

=== S06: OPTIONS FLOW TABLE ===
{% for opt in unusual_options %}
  {{ opt.stock }} {{ opt.strike }} {{ opt.type }} {{ opt.volume }}
  {{ opt.vol_vs_avg }} {{ opt.oi_change }} {{ opt.iv_rank }}
  {{ opt.premium }} {{ opt.signal }} {{ opt.ai_score }}
{% endfor %}
{{ options_summary | safe }}          # From options_agent

=== S07: CORRELATION MATRIX ===
{{ correlation_assets | tojson }}     # ["Nifty","BankNifty",...]
{{ correlation_data | tojson }}       # 7×7 nested array
{{ correlation_anomaly | safe }}      # AI interpretation text

=== S08: BLOCK DEALS ===
{% for deal in block_deals %}
  {{ deal.ticker }} {{ deal.detail }}
  {{ deal.quantity }} {{ deal.price }} {{ deal.type }}  # "Buy"/"Sell"
  {{ deal.color }}                    # green or red
{% endfor %}
{{ block_deals_summary | safe }}      # AI interpretation

=== S09: GAP STATISTICS ===
{{ gap_size_chart_data | tojson }}
{{ gap_expiry_chart_data | tojson }}
{{ gap_analysis_narrative | safe }}   # From narrative_agent or template-generated

=== S10: SENTIMENT ===
Twitter panel:
{% for s in social_sentiment %}
  {{ s.hashtag }} {{ s.count }} {{ s.score_pct }}
  {{ s.bar_color }}                   # green/red/amber based on score
{% endfor %}

TV panel:
{% for tv in tv_analyst_calls %}
  {{ tv.analyst }} — {{ tv.channel }}
  {{ tv.call_text }}
  {% if tv.conflict %}
    {{ tv.conflict }}                 # From conflict_agent
  {% endif %}
{% endfor %}
{{ tv_accuracy_line }}                # "30-day accuracy: Sukhani 61% | ..."

=== S11: STOCKS TO AVOID ===
{% for a in avoid_list %}
  {{ a.ticker }}
  {{ a.reason | safe }}               # HTML with <strong> tags
  {{ a.flag_type }}                   # "Short Squeeze", "IV Crush Risk", etc.
{% endfor %}

=== S12: EXPIRY PLAYBOOK ===
Stats cards:
  {{ expiry.gap_sustain_rate }}
  {{ expiry.max_pain_nifty }}
  {{ expiry.pcr_nifty }}
  {{ expiry.total_premium }}
  {{ expiry.gap_fill_probability }}
  {{ expiry.daily_theta_atm }}
OI chart: {{ oi_chart_data | tojson }}
Narrative: {{ expiry_narrative | safe }}

=== S13: FII/DII TRACKER ===
Summary cards:
  {{ fii_cash_prev }} {{ fii_cash_5d }}
  {{ dii_cash_prev }} {{ dii_cash_5d }}
  {{ fii_futures }} {{ fii_futures_contracts }}
  {{ fii_options }} {{ fii_options_contracts }}
Chart: {{ fii_dii_chart_data | tojson }}
Summary: {{ fii_dii_summary | safe }}  # From options_agent or narrative_agent

=== S14: SCENARIO PLAYBOOK ===
{% for s in scenarios %}
  {{ s.label }}       # "Scenario A — Bull Case"
  {{ s.color }}       # green/amber/red
  {{ s.probability }} # "45%"
  {{ s.trigger | safe }}
  {{ s.actions | safe }}
  {{ s.exit | safe }}
{% endfor %}

=== S15: WATCHLIST QUEUE ===
{% for alert in watchlist_alerts %}
  {{ alert.time }}        # "09:00"
  {{ alert.priority }}    # "critical", "high", ""
  {{ alert.content | safe }}
{% endfor %}

=== S16: EVENTS CALENDAR ===
{% for ev in events_calendar %}
  {{ ev.severity }}       # "hi", "med", ""
  {{ ev.time }}           # "MON 09:00"
  {{ ev.text | safe }}
{% endfor %}

=== S17: RISK SIZING ===
  {{ risk.max_risk_per_trade }}   # "₹2.4L"
  {{ risk.nifty_atr }}            # "186 pts"
  {{ risk.recommended_lots }}     # "2 lots"
  {{ risk.expiry_adj_factor }}    # "0.75×"
  {{ risk_narrative | safe }}

=== FOOTER ===
  {{ generated_at }}
  {{ signal_count }}
  {{ pattern_match_count }}
  {{ contagion_chain_count }}
```

---

## FIX 7: Explicit Reference HTML Embedding Instruction

### Add to the build sequence (before Phase 5):

```
CRITICAL STEP: Before building the Jinja2 template, you MUST:

1. The reference file `alpha-edge-v2.html` will be provided to you as input.
   This is the EXACT visual design the output must match.

2. Copy the ENTIRE <style> block (600+ lines of CSS) verbatim into the 
   Jinja2 template. Do NOT modify any CSS class names, colors, fonts, 
   spacing, or layout rules.

3. Copy the ENTIRE <script> block (Chart.js initialization) as the base,
   then replace hardcoded data arrays with {{ variable | tojson }} Jinja2 tags.

4. For the HTML body: keep every structural div, class name, and HTML element.
   ONLY replace hardcoded text/numbers with {{ variable }} tags.

5. Preserve ALL of these design elements exactly:
   - Noise texture overlay (body::before with SVG filter)
   - Fade-up animations on sections
   - Pulsing glow on masthead mark
   - Blinking live dot
   - Phosphor green (#00E87B) as primary accent
   - IBM Plex Mono for data, Instrument Serif for headings, Libre Franklin for body
   - Hover effects on cards and table rows
   - Responsive breakpoints at 1100px and 800px
   - Dark scrollbar styling
   - Selection color (green on void)

6. The correlation matrix heatmap is JavaScript-generated (not template HTML).
   Keep the JS code that dynamically builds the table and applies colors.
   Only change the data source from hardcoded to {{ correlation_data | tojson }}.

7. Report filename: alpha_edge_YYYY-MM-DD.html (e.g. alpha_edge_2026-03-30.html)
```

---

## FIX 8: Update CLAUDE.md — Add Missing Context

### Append these sections to CLAUDE.md:

```markdown
## Feature Module Dependency Chain

The feature pipeline must execute in this order (some modules depend on others):

1. technical.py (needs: OHLCV data)
2. options_analytics.py (needs: options chain data)
3. gap_analysis.py (needs: technical levels, macro data)
4. stock_screener.py (needs: gap_analysis, options_analytics, sector_rotation)
5. sector_rotation.py (needs: stock data, FII/DII flows)
6. correlation.py (needs: macro data, historical prices)
7. pattern_matching.py (needs: stock_screener output, historical fingerprints)
8. avoid_list.py (needs: stock data, options, block deals, news)
9. expiry_analysis.py (needs: options_analytics, gap_analysis)
10. confidence_score.py (needs: ALL of the above)
11. contagion_chain.py (needs: macro data catalyst detection)
12. risk_sizing.py (needs: confidence_score, VIX, ATR)
13. events_calendar.py (needs: date, earnings calendar)
14. watchlist_queue.py (needs: stock_screener, nifty levels, expiry)
15. sentiment.py (needs: social data, news data)

## Report Sections → Data Source Mapping

| Section | Data Source | AI Agent? |
|---------|-----------|-----------|
| Masthead pills | macro dashboard | No |
| Hero mood cards | macro dashboard + sparklines | No |
| S01 Narrative | ALL features | YES — narrative_agent |
| S02 Levels | technical.py | No |
| S03 Gap-Up Setups | stock_screener.py + pattern_matching.py | YES — stock_analyst_agent |
| S04 Sector Rotation | sector_rotation.py | No |
| S05 Contagion | contagion_chain.py | No |
| S06 Options Flow | options_analytics.py | YES — options_agent |
| S07 Correlation | correlation.py | No (JS-generated heatmap) |
| S08 Block Deals | block_deals.py collector | No |
| S09 Gap Stats | gap_analysis.py | No |
| S10 Sentiment | sentiment.py + tv_analysts.py | YES — conflict_agent |
| S11 Avoid List | avoid_list.py | No |
| S12 Expiry | expiry_analysis.py | No |
| S13 FII/DII | fii_dii.py collector | No |
| S14 Scenarios | ALL features | YES — scenario_agent |
| S15 Watchlist | watchlist_queue.py | YES — watchlist_agent |
| S16 Events | events_calendar.py | No |
| S17 Risk Sizing | risk_sizing.py | No |

## Sections That Need AI vs Pure Data

AI agents only write text for 6 of 17 sections. The other 11 are pure 
data-driven templates. If Groq API fails, those 11 sections still render 
perfectly. The 6 AI sections show placeholder text: "AI narrative unavailable — 
data shown below."
```

---

## FIX 9: Add Missing News-to-Ticker Tagging

### In `data/collectors/news.py`, add ticker extraction:
```python
# After collecting headlines, tag each with relevant tickers/sectors:
TICKER_KEYWORDS = {
    "INDIGO": ["indigo", "interglobe", "aviation", "airline", "atf"],
    "RELIANCE": ["reliance", "ril", "jio", "reliance industries"],
    "TCS": ["tcs", "tata consultancy"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ASIANPAINT": ["asian paints", "asianpaint"],
    # ... all 50 stocks
    # Macro keywords:
    "CRUDE": ["crude", "brent", "opec", "oil price", "petroleum"],
    "RBI": ["rbi", "monetary policy", "rate cut", "repo rate"],
    "FED": ["fed", "federal reserve", "fomc", "powell"],
}

def tag_headline(headline: str) -> List[str]:
    """Return list of tickers/themes mentioned in headline"""
    headline_lower = headline.lower()
    return [ticker for ticker, keywords in TICKER_KEYWORDS.items()
            if any(kw in headline_lower for kw in keywords)]
```

---

## FIX 10: Add Report Opening in Browser

### In `main.py`, after saving the report:
```python
import webbrowser
import os

# After report is saved:
report_path = renderer.save(html_report)
absolute_path = os.path.abspath(report_path)
webbrowser.open(f"file://{absolute_path}")
logger.info(f"📂 Report opened in browser: {absolute_path}")
```

---

## FINAL CHECKLIST — Verify Before Building

Before Claude Code starts implementing, verify these are ALL present:

```
☐ CLAUDE.md in project root (with dependency chain + section mapping)
☐ alpha-edge-v2.html provided as reference (will be pasted into Claude Code)
☐ config/constants.py has ALL 50 Nifty stocks with sectors
☐ 7 data collectors (market, stocks, options, fii_dii, block_deals, news, sentiment)
  + 1 new collector (tv_analysts)
☐ 15 feature modules (technical, options_analytics, gap_analysis, stock_screener, 
  sector_rotation, correlation, pattern_matching, avoid_list, expiry_analysis, 
  confidence_score, contagion_chain, risk_sizing, events_calendar, 
  watchlist_queue, sentiment)
☐ 6 LangGraph agents (narrative, stock_analyst, options, scenario, conflict, watchlist)
☐ Complete ComputedFeatures model with ALL fields for all 17 sections
☐ Jinja2 template converted from reference HTML with ALL 17 sections templated
☐ Chart.js data prep for all 12 charts with exact color codes
☐ SQLite schema with 4 tables + indexes
☐ Backfill script for 2+ years of historical data
☐ main.py with full pipeline + browser opening
☐ Report filename: alpha_edge_YYYY-MM-DD.html
```
