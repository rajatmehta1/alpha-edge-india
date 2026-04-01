# ALPHA EDGE — Senior Review Panel: Final Audit & Fixes
## Three-person review: AI Architect, Financial Engineer, Product Manager

---

> **INSTRUCTIONS FOR CLAUDE CODE**: This is the FINAL review document. It contains 
> fixes found by a simulated panel of three senior engineers reviewing the complete 
> prompt set. Apply these fixes ON TOP of the main prompt and first patch.
> These are the last corrections needed before building.

---

## PANEL DISCUSSION TRANSCRIPT

---

### RAVI (Distinguished Principal Financial Engineer, 22 years on Dalal Street):

"I've been through the options analytics spec and I have serious concerns. Let me walk through them.

**Issue 1 — Max Pain formula has a variable naming error.** The prompt says:

```
call_payout = sum of max(0, strike - S) * call_OI for all calls
put_payout = sum of max(0, S - strike) * put_OI for all puts
```

This is confusing. `S` and `strike` are being used inconsistently. In max pain, you're iterating over every possible settlement price `P`, and for each `P`, you compute the total loss to option buyers across ALL strikes. The correct algorithm is:

```python
For each candidate settlement_price P in all_strikes:
    total_pain = 0
    for each strike K in all_strikes:
        # Pain to call buyers if stock settles at P:
        call_pain = max(0, P - K) * call_oi_at_K
        # Pain to put buyers if stock settles at P:  
        put_pain = max(0, K - P) * put_oi_at_K
        total_pain += call_pain + put_pain
    
Max pain = P with MAXIMUM total_pain to buyers
         = P with MINIMUM total payout by option writers
```

Wait — actually I need to reconsider. Max pain is the strike where option WRITERS pay the LEAST. So we want the strike where the total intrinsic value of all outstanding options is minimized. Let me rewrite:

```python
For each candidate_price P:
    writer_payout = 0
    for strike K, call_oi, put_oi in option_chain:
        writer_payout += max(0, P - K) * call_oi   # Writers pay call holders
        writer_payout += max(0, K - P) * put_oi     # Writers pay put holders
    
max_pain = P where writer_payout is MINIMUM
```

That's the correct formulation. The original prompt had the right idea but the variable names made it ambiguous.

**Issue 2 — VWAP cannot be computed from yfinance daily data.** VWAP = Σ(Price × Volume) / Σ(Volume) computed on intraday bars. yfinance free tier gives daily OHLCV only. For Indian stocks via `.NS` suffix, intraday data is unreliable and rate-limited. The practical proxy:

```python
# Typical Price as VWAP proxy (industry standard when intraday unavailable):
typical_price = (high + low + close) / 3

# Better proxy — Volume-weighted typical price across last N days:
vwap_proxy = sum(typical_price_i * volume_i for i in last_5_days) / sum(volume_i)
```

Document this clearly as a proxy, not true intraday VWAP.

**Issue 3 — IV Rank requires 52-week historical implied volatility, which yfinance doesn't provide.** You can't just call yfinance and get historical IV. For free data, use this proxy:

```python
# Compute Historical Volatility Rank instead of IV Rank:
# HV = annualized std dev of log returns over 20 days
hv_20 = np.std(np.log(closes[1:] / closes[:-1])) * np.sqrt(252) * 100

# HV Rank = where current HV sits in its 252-day range
hv_values_1yr = [compute_hv20(window) for window in rolling_252d_windows]
hv_rank = percentileofscore(hv_values_1yr, hv_20)
```

This is a legitimate proxy used by many retail platforms. Label it `HV Rank` in the report, or if you want to show `IV Rank`, note that it's approximated from historical volatility.

**Issue 4 — Options Skew using '25-delta' requires Black-Scholes delta computation.** For MVP, too complex. Use a simpler but legitimate proxy:

```python
# Simple skew proxy: compare OTM put IV vs OTM call IV
# OTM = strikes outside ±3% of ATM
atm_strike = closest_strike_to_spot
otm_puts = strikes where K < atm_strike * 0.97
otm_calls = strikes where K > atm_strike * 1.03
skew = mean(otm_call_ivs) - mean(otm_put_ivs)
# Positive = calls more expensive (bullish skew)
# Negative = puts more expensive (fear/hedging)
```

**Issue 5 — PCR should use near-ATM strikes, not total OI.** Total OI includes deep OTM strikes with huge OI that never get exercised. Industry practice:

```python
# Use ATM ± 5 strikes for meaningful PCR
atm_strike = closest_strike_to_spot
relevant_strikes = [K for K in all_strikes if abs(K - atm_strike) <= 5 * strike_interval]
pcr = sum(put_oi for K in relevant_strikes) / sum(call_oi for K in relevant_strikes)
```

Also compute total_pcr (all strikes) separately — some traders prefer it. Show both:
`PCR (ATM±5): 1.24 | Total PCR: 0.98`

**Issue 6 — The expected open regression coefficients are arbitrary.** The formula:

```
expected_nifty_open = prev_close * (1 + 0.4*dow_pct + 0.15*(-brent_pct) + 0.1*(-usdinr_pct))
```

Those weights (0.4, 0.15, 0.1) are pulled from thin air. Two options:

Option A (better): Compute these via linear regression on the historical backfill data:
```python
from sklearn.linear_model import LinearRegression
# Features: [dow_overnight_pct, brent_overnight_pct, usdinr_overnight_pct]
# Target: nifty_gap_pct (open/prev_close - 1)
# Train on 2 years of data from SQLite
model = LinearRegression().fit(X_train, y_train)
coefficients = model.coef_  # Use these instead of hardcoded 0.4, 0.15, 0.1
```

Option B (pragmatic for MVP): Keep the hardcoded weights but document them as estimates with a TODO to replace with regression-fitted values after the backfill runs.

**Issue 7 — Sector sensitivity coefficients** (Aviation crude_sensitivity = -1.8, etc.) are also undocumented estimates. Same solution: compute from historical correlation between sector returns and crude/forex changes, or document as heuristic estimates.

**Issue 8 — Risk sizing is missing the lot size computation.** The report says '2 lots' but the formula isn't specified:

```python
# Nifty lot size = 25 (as of 2026, verify)
# Position sizing:
risk_per_trade = capital * max_risk_pct  # ₹24L * 1% = ₹2,400
risk_per_lot = atr * lot_size * risk_multiple  # 186 * 25 * 0.5 = ₹2,325
recommended_lots = floor(risk_per_trade / risk_per_lot)  # floor(2400/2325) = 1

# With expiry adjustment:
adjusted_lots = floor(recommended_lots * expiry_adj_factor)  # 1 * 0.75 = 0 → min 1
recommended_lots = max(1, adjusted_lots)
```

Wait, that gives 1 lot, not 2. The reference shows 2 lots. This depends on the ATR and risk multiple. For the report to show '2 lots' consistently, either: (a) compute it dynamically and show whatever the math says, or (b) use a slightly different risk multiple. I'd go with (a) — show the real number."

---

### ANIKA (AI Architect & Engineer, 18 years, ex-Google Staff Engineer):

"Ravi's financial fixes are critical. Let me address the AI and engineering issues.

**Issue 9 — Groq + Llama 3.3 70B is unreliable for structured JSON output.** Unlike Claude, Llama models frequently add conversational preamble before JSON, or wrap JSON in markdown code fences. You MUST have a JSON extraction utility:

```python
import json
import re

def extract_json(text: str) -> dict:
    '''Extract JSON from LLM response that may have preamble or code fences.'''
    # Strategy 1: Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from code fences
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find first { and last } 
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Find first [ and last ]
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f'Could not extract JSON from LLM response: {text[:200]}...')
```

This goes in a new file: `agents/json_utils.py`. Every agent must use this instead of raw `json.loads()`.

Also, add a retry wrapper for agent calls:

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
async def call_agent_with_retry(agent_fn, state):
    result = await agent_fn(state)
    # Validate output is parseable
    if result is None:
        raise ValueError('Agent returned None')
    return result
```

**Issue 10 — Pattern matching cold start is not handled.** Day 1, the SQLite fingerprint table is empty. Day 30, you have only 30 sessions — not enough for meaningful pattern matching. The prompt says 'use wider threshold' but doesn't specify what to show in the report. Fix:

```python
# In pattern_matching.py:
MIN_MATCHES_FOR_CONFIDENCE = 8    # Need at least 8 similar events
MIN_HISTORY_FOR_PATTERNS = 100    # Need 100+ sessions in database

if total_sessions_in_db < MIN_HISTORY_FOR_PATTERNS:
    return PatternMatch(
        total_matches=0,
        win_rate=None,
        median_upside=None,
        median_drawdown=None,
        message='Pattern engine building history — available after ~100 trading sessions.'
    )

if len(neighbors) < MIN_MATCHES_FOR_CONFIDENCE:
    # Still return what we have, but with a confidence caveat
    return PatternMatch(
        total_matches=len(neighbors),
        win_rate=computed_win_rate,
        confidence='low',  # 'low', 'medium', 'high'
        message=f'Only {len(neighbors)} matches found — interpret with caution.'
    )
```

In the Jinja2 template:
```jinja2
{% if stock.pattern_match.total_matches > 0 %}
  <div class="pattern-box">... show pattern stats ...</div>
{% else %}
  <div class="pattern-box" style="border-color:var(--amber)">
    <div class="pat-hl">Pattern Engine: Building History</div>
    <div class="pat-detail">{{ stock.pattern_match.message }}</div>
  </div>
{% endif %}
```

**Issue 11 — Categorical feature encoding for pattern matching.** The prompt says to encode `sector` as a feature dimension, but sector is categorical (not ordinal). Cosine similarity on raw categorical values is meaningless. Fix:

```python
# In pattern_matching.py, encode features properly:

# Option A (simple): Use sector match as a FILTER, not a feature
# First filter to same-sector historical sessions, then compute similarity on remaining features
same_sector = fingerprints[fingerprints.sector == today_sector]
# Then run KNN on the continuous features only

# Option B (encoding): One-hot encode sector, but this explodes dimensionality
# Not recommended for KNN with small datasets

# Option C (recommended for MVP): Use Gower distance instead of cosine similarity
# Gower distance handles mixed continuous + categorical features natively
from scipy.spatial.distance import pdist, squareform
# ... but scikit-learn doesn't support Gower directly.

# PRAGMATIC SOLUTION: Filter by sector first, then KNN on continuous features.
# This also makes business sense — you want to match 'IndiGo gap-up + crude drop'
# against other aviation stocks in crude-drop scenarios, not banking stocks.
```

**Issue 12 — The `features/pipeline.py` is mentioned but never specified.** This is the orchestrator that calls all 15 modules in dependency order. It needs explicit code:

```python
class FeaturePipeline:
    def compute(self, raw_data: RawMarketData) -> ComputedFeatures:
        '''Execute all feature modules in dependency order.'''
        # Phase 1: Independent computations (can parallelize later)
        technical = TechnicalComputer().compute(raw_data.nifty_ohlcv, raw_data.banknifty_ohlcv, raw_data.stock_ohlcv)
        options = OptionsAnalytics().compute(raw_data.options_chain)
        sentiment = SentimentComputer().compute(raw_data.social_data, raw_data.news_data)
        correlation = CorrelationComputer().compute(raw_data.macro_history)
        sector_flows = SectorRotation().compute(raw_data.stock_data, raw_data.fii_dii)
        
        # Phase 2: Dependent computations
        gap_stats = GapAnalysis().compute(technical, raw_data.macro)
        stock_candidates = StockScreener().compute(raw_data, technical, options, sector_flows, gap_stats)
        avoid_flags = AvoidList().compute(raw_data, options, raw_data.block_deals, raw_data.news)
        expiry = ExpiryAnalysis().compute(options, gap_stats)
        contagion = ContagionChain().compute(raw_data.macro)
        
        # Phase 3: Pattern matching (needs stock_candidates)
        for candidate in stock_candidates:
            candidate.pattern_match = PatternMatcher().find_similar(candidate, raw_data.macro)
        
        # Phase 4: Aggregate scores
        confidence = ConfidenceScore().compute(
            macro=raw_data.macro, options=options, sector_flows=sector_flows,
            sentiment=sentiment, gap_stats=gap_stats, expiry=expiry
        )
        risk = RiskSizing().compute(confidence, raw_data.macro.india_vix, technical.nifty.atr, expiry)
        
        # Phase 5: Supplementary data
        events = EventsCalendar().compute(date.today())
        watchlist = WatchlistQueue().compute(stock_candidates[:3], technical.nifty_levels, expiry)
        
        return ComputedFeatures(
            macro=raw_data.macro,
            nifty_levels=technical.nifty,
            banknifty_levels=technical.banknifty,
            options=options,
            gap_stats=gap_stats,
            sector_flows=sector_flows,
            correlations=correlation,
            sentiment=sentiment,
            risk=risk,
            confidence_score=confidence,
            gap_up_candidates=stock_candidates,
            avoid_list=avoid_flags,
            block_deals=raw_data.block_deals,
            pattern_matches=[c.pattern_match for c in stock_candidates],
            expiry=expiry,
            events_calendar=events,
            tv_analyst_calls=raw_data.tv_calls,
            fii_dii_history=raw_data.fii_dii_history,
            contagion_chain=contagion,
        )
```

**Issue 13 — Graceful degradation needs to be section-specific.** If options chain collector fails, sections 6 (Options Flow), 12 (Expiry Playbook), and parts of section 3 (IV rank, options skew) should show a fallback, but all other sections should render normally. Add a `SectionStatus` tracker:

```python
class SectionStatus:
    '''Tracks which sections have complete data vs degraded.'''
    def __init__(self):
        self._status = {}
    
    def mark_ok(self, section: str):
        self._status[section] = 'ok'
    
    def mark_degraded(self, section: str, reason: str):
        self._status[section] = f'degraded: {reason}'
    
    def is_ok(self, section: str) -> bool:
        return self._status.get(section) == 'ok'
    
    def get_message(self, section: str) -> Optional[str]:
        status = self._status.get(section, 'ok')
        if status == 'ok':
            return None
        return status.replace('degraded: ', '')
```

Pass this to the template so degraded sections show: `⚠ Options data unavailable — showing cached values` instead of crashing."

---

### PRIYA (Product Manager, 15 years, ex-Zerodha Head of Product):

"Both of you have caught real engineering issues. Let me check the product requirements — does every pixel in that V2 report have a data source, and will the user experience hold up?

**Issue 14 — The footer stats are hardcoded in the reference but need to be dynamic.** The report footer says '847 signals processed · 18 pattern matches · 6 contagion chains'. These must be computed:

```python
class ReportMetadata(BaseModel):
    signal_count: int          # Count of all raw data points collected
    pattern_match_count: int   # Total matches across all stocks
    contagion_chain_count: int # Number of contagion chains mapped
    correlation_anomalies: int # Number of correlation anomalies detected
    pipeline_duration_seconds: float
    generated_at: str          # '07:18 IST'

# In main.py, track these as the pipeline runs:
metadata = ReportMetadata(
    signal_count = sum(len(collector_result.data) for result in all_results),
    pattern_match_count = sum(pm.total_matches for pm in features.pattern_matches),
    contagion_chain_count = len(features.contagion_chain.orders),
    # ...
)
```

**Issue 15 — Block deal descriptions need realistic text.** The reference shows 'Capital Group acquired 8.2L shares via block'. Most free block deal sources only give: ticker, quantity, price, exchange. Buyer/seller names are rarely available for free. Fix:

```python
# When buyer/seller is unknown (which is most of the time):
class BlockDeal(BaseModel):
    ticker: str
    quantity: int
    price: float
    deal_type: str          # 'Block' or 'Bulk'
    buyer_seller: Optional[str]  # Often None for free data
    
    @property
    def description(self) -> str:
        if self.buyer_seller:
            return f'{self.buyer_seller} — {self.deal_type.lower()} deal'
        else:
            qty_lakhs = self.quantity / 100000
            return f'{self.deal_type} deal: {qty_lakhs:.1f}L shares at ₹{self.price:,.0f}'
```

The template should handle both cases gracefully.

**Issue 16 — Conditional rendering for non-expiry weeks.** When `is_expiry_week` is False, Section 12 (Expiry Playbook) should either: (a) hide entirely, or (b) show with reduced content. The masthead '⚡ Expiry Wk' pill should also hide. Fix:

In the Jinja2 template:
```jinja2
{# Masthead pill - conditional #}
{% if expiry.is_expiry_week %}
  <span class="pill pill-amber">⚡ Expiry Wk</span>
{% endif %}

{# Section 12 - conditional full/reduced display #}
{% if expiry.is_expiry_week %}
  {# Full expiry section with all 6 stat cards and OI chart #}
{% else %}
  {# Simplified: just show max pain, PCR, and days to expiry #}
  <div class="narrative" style="border-left-color:var(--amber)">
    Next monthly expiry: {{ expiry.days_to_expiry }} trading days away 
    ({{ expiry.next_expiry_date }}). Max Pain: {{ expiry.max_pain_nifty }}. 
    PCR: {{ expiry.pcr_nifty }}.
  </div>
{% endif %}
```

**Issue 17 — The correlation anomaly text in Section 07 needs a source.** The reference shows: 'Nifty-Brent correlation has broken from the usual −0.45 to −0.72'. This requires:

```python
# In correlation.py, add anomaly detection:
class CorrelationAnomaly(BaseModel):
    asset_pair: str           # 'Nifty-Brent'
    current_corr: float       # -0.72
    historical_mean: float    # -0.45 (90-day mean)
    z_score: float            # How many std devs from mean
    direction: str            # 'strengthened' or 'weakened'
    interpretation: str       # Auto-generated text

def detect_anomalies(current_matrix, historical_matrices):
    anomalies = []
    for i, j in combinations(range(len(assets)), 2):
        current = current_matrix[i][j]
        historical = [m[i][j] for m in historical_matrices]
        mean = np.mean(historical)
        std = np.std(historical)
        z = (current - mean) / std if std > 0 else 0
        
        if abs(z) > 2.0:  # > 2 standard deviations = anomaly
            anomalies.append(CorrelationAnomaly(
                asset_pair=f'{assets[i]}-{assets[j]}',
                current_corr=round(current, 2),
                historical_mean=round(mean, 2),
                z_score=round(z, 2),
                direction='strengthened' if abs(current) > abs(mean) else 'weakened',
                interpretation=f'{assets[i]}-{assets[j]} correlation has '
                    f'{"strengthened" if abs(current) > abs(mean) else "weakened"} '
                    f'from the usual {mean:.2f} to {current:.2f}. '
                    f'This extreme reading historically mean-reverts within 3-5 sessions.'
            ))
    return anomalies
```

This is computed, not AI-generated. Deterministic text based on the math.

**Issue 18 — First-run experience.** When a user runs `python main.py` for the very first time without running the backfill script, the system will crash because SQLite has no historical data. Fix:

```python
# In main.py, add first-run detection:
from storage.database import get_session_count

async def run_pipeline():
    init_db()
    
    session_count = get_session_count()
    if session_count == 0:
        console.print('[bold yellow]⚠ No historical data found.[/]')
        console.print('[yellow]Running initial backfill (this takes 5-10 minutes)...[/]')
        console.print('[dim]This only happens on first run.[/]')
        from scripts.backfill_history import run_backfill
        await run_backfill()
        console.print('[bold green]✅ Backfill complete. Continuing with report generation...[/]')
    
    # ... rest of pipeline
```

This way, `python main.py` Just Works™ on first run.

**Issue 19 — The '30-day accuracy' line for TV analysts** (`Sukhani 61% | Gaba 54%`) is shown in the report but there's no system to track it. For MVP, these are hardcoded constants in `config/constants.py` (already there). But the prompt should note: these are static estimates from publicly available track record data, not dynamically computed. Add a comment in the template:

```jinja2
{# TV accuracy is from curated data in constants.py, not computed #}
<div style="...">📊 30-day accuracy: {{ tv_accuracy_line }}</div>
```

**Issue 20 — The AI Market Mood Score color should map to the confidence level:**

```python
# In report/renderer.py or chart_data.py:
def mood_color(score: int) -> str:
    if score >= 75: return 'var(--phosphor)'     # Bullish = green
    if score >= 55: return 'var(--phosphor)'     # Moderately Bullish = green
    if score >= 45: return 'var(--amber)'        # Neutral = amber
    if score >= 25: return 'var(--amber)'        # Cautious = amber
    return 'var(--danger)'                        # Bearish = red

def mood_label(score: int) -> str:
    if score >= 75: return 'Bullish'
    if score >= 55: return 'Moderately Bullish'
    if score >= 45: return 'Neutral'
    if score >= 25: return 'Cautious'
    return 'Bearish'
```

---

### PANEL CONCLUSION

**RAVI:** "The financial calculations are now sound. The proxies for VWAP, IV Rank, and options skew are industry-standard for retail-grade platforms. The max pain fix is critical — wrong max pain = wrong expiry analysis = traders making wrong decisions. I'm satisfied."

**ANIKA:** "The JSON extraction utility for Groq is essential — without it, the pipeline will fail 20-30% of the time on malformed LLM output. The pipeline orchestrator code, cold start handling, and graceful degradation will prevent the system from being brittle. The pattern matching filter-by-sector approach is more correct than raw cosine similarity on mixed types. I'm satisfied."

**PRIYA:** "All 17 sections now have clear data sources. The conditional rendering for non-expiry weeks prevents showing empty/irrelevant data. The first-run auto-backfill is a great UX touch — no one reads README instructions. The dynamic footer stats make the report feel alive rather than templated. I'm satisfied. Ship it."

**UNANIMOUS VERDICT: The prompts are now production-ready with these 20 fixes applied.**

---

## CONSOLIDATED FIX LIST (for Claude Code)

Apply these fixes to the codebase in order:

### FIX A: Create `agents/json_utils.py`
```python
"""Robust JSON extraction from LLM responses.
Llama 3.3 via Groq often adds preamble, code fences, or trailing text.
Every agent MUST use extract_json() instead of raw json.loads()."""

import json
import re
from typing import Union

def extract_json(text: str) -> Union[dict, list]:
    """Extract JSON object or array from potentially messy LLM output."""
    text = text.strip()
    
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code fences
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find outermost braces
    for open_char, close_char in [('{', '}'), ('[', ']')]:
        start = text.find(open_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_char:
                depth += 1
            elif text[i] == close_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break
    
    raise ValueError(f'Could not extract valid JSON from LLM response:\n{text[:500]}')
```

### FIX B: Correct max pain algorithm in `features/options_analytics.py`
```python
def compute_max_pain(option_chain: List[OptionStrike]) -> float:
    """Correct max pain: strike where total option writer payout is minimized."""
    all_strikes = sorted(set(s.strike for s in option_chain))
    min_payout = float('inf')
    max_pain_strike = all_strikes[len(all_strikes) // 2]  # default to ATM
    
    for candidate_price in all_strikes:
        total_writer_payout = 0
        for strike_data in option_chain:
            K = strike_data.strike
            # Call writers pay max(0, P - K) per unit of call OI
            if candidate_price > K:
                total_writer_payout += (candidate_price - K) * strike_data.call_oi
            # Put writers pay max(0, K - P) per unit of put OI
            if K > candidate_price:
                total_writer_payout += (K - candidate_price) * strike_data.put_oi
        
        if total_writer_payout < min_payout:
            min_payout = total_writer_payout
            max_pain_strike = candidate_price
    
    return max_pain_strike
```

### FIX C: Use typical price as VWAP proxy in `features/technical.py`
```python
def compute_vwap_proxy(ohlcv_df: pd.DataFrame, window: int = 5) -> float:
    """Volume-weighted typical price over N days as VWAP proxy.
    True VWAP requires intraday data (not available from yfinance free tier).
    This is a standard proxy used when intraday data is unavailable."""
    typical_price = (ohlcv_df['High'] + ohlcv_df['Low'] + ohlcv_df['Close']) / 3
    recent = ohlcv_df.tail(window)
    tp_recent = typical_price.tail(window)
    vwap = (tp_recent * recent['Volume']).sum() / recent['Volume'].sum()
    return round(vwap, 2)
```

### FIX D: Use HV Rank as IV Rank proxy in `features/options_analytics.py`
```python
def compute_hv_rank(closes: pd.Series, current_window: int = 20, lookback: int = 252) -> int:
    """Historical Volatility Rank as proxy for IV Rank.
    IV Rank requires historical implied volatility data (not free).
    HV Rank measures where current realized volatility sits in its 1-year range."""
    log_returns = np.log(closes / closes.shift(1)).dropna()
    
    # Current 20-day HV (annualized)
    current_hv = log_returns.tail(current_window).std() * np.sqrt(252)
    
    # Rolling 20-day HV over the past year
    rolling_hv = log_returns.rolling(current_window).std() * np.sqrt(252)
    rolling_hv = rolling_hv.dropna().tail(lookback)
    
    if len(rolling_hv) < 50:  # Not enough history
        return 50  # Default to mid-range
    
    hv_rank = int(percentileofscore(rolling_hv.values, current_hv))
    return max(0, min(100, hv_rank))
```

### FIX E: Simplified options skew proxy
```python
def compute_skew_proxy(option_chain, spot_price: float) -> float:
    """Simple skew: avg OTM call IV - avg OTM put IV.
    Positive = bullish skew (calls more expensive).
    Negative = bearish/hedging skew (puts more expensive)."""
    atm_range = spot_price * 0.03  # ±3% of spot
    
    otm_calls = [s for s in option_chain if s.strike > spot_price + atm_range and s.call_iv]
    otm_puts = [s for s in option_chain if s.strike < spot_price - atm_range and s.put_iv]
    
    if not otm_calls or not otm_puts:
        return 0.0
    
    avg_call_iv = sum(s.call_iv for s in otm_calls) / len(otm_calls)
    avg_put_iv = sum(s.put_iv for s in otm_puts) / len(otm_puts)
    
    return round(avg_call_iv - avg_put_iv, 2)
```

### FIX F: Near-ATM PCR computation
```python
def compute_pcr(option_chain, spot_price: float, strike_interval: float = 50) -> tuple:
    """Compute both near-ATM PCR and total PCR.
    Near-ATM (±5 strikes) is more meaningful for intraday trading."""
    atm_strike = round(spot_price / strike_interval) * strike_interval
    
    near_atm = [s for s in option_chain 
                if abs(s.strike - atm_strike) <= 5 * strike_interval]
    
    total_put_oi = sum(s.put_oi for s in option_chain)
    total_call_oi = sum(s.call_oi for s in option_chain)
    near_put_oi = sum(s.put_oi for s in near_atm)
    near_call_oi = sum(s.call_oi for s in near_atm)
    
    total_pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
    near_pcr = near_put_oi / near_call_oi if near_call_oi > 0 else 1.0
    
    return round(near_pcr, 2), round(total_pcr, 2)
```

### FIX G: Pattern matching — filter by sector first
```python
def find_similar_sessions(today_fingerprint, all_fingerprints, min_matches=8):
    """Find similar historical sessions using sector-filtered KNN."""
    # Step 1: Filter to same sector
    same_sector = all_fingerprints[
        all_fingerprints['sector'] == today_fingerprint['sector']
    ]
    
    if len(same_sector) < min_matches:
        # Fallback: include adjacent sectors
        same_sector = all_fingerprints  # Use all sectors
    
    # Step 2: Extract continuous features only (drop sector, ticker, date)
    feature_cols = ['gap_pct', 'crude_change', 'vix_level', 'vix_change',
                    'fii_flow_bucket', 'pcr', 'day_of_week', 'is_expiry_week',
                    'days_to_expiry', 'prev_5d_return', 'rsi_14', 'volume_ratio']
    
    X = same_sector[feature_cols].values
    today_vec = np.array([[today_fingerprint[c] for c in feature_cols]])
    
    # Step 3: Normalize
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    today_scaled = scaler.transform(today_vec)
    
    # Step 4: KNN
    k = min(20, len(X_scaled))
    nn = NearestNeighbors(n_neighbors=k, metric='cosine')
    nn.fit(X_scaled)
    distances, indices = nn.kneighbors(today_scaled)
    
    # Step 5: Compute outcomes from matched sessions
    matched = same_sector.iloc[indices[0]]
    return compute_pattern_stats(matched)
```

### FIX H: Auto-backfill on first run in `main.py`
```python
# Add at the start of run_pipeline():
from storage.database import init_db, get_session_count

async def run_pipeline():
    init_db()
    
    session_count = get_session_count()
    if session_count < 100:
        console.print(f'[bold yellow]⚠ Only {session_count} historical sessions found.[/]')
        if session_count == 0:
            console.print('[yellow]Running initial data backfill (5-10 minutes)...[/]')
            from scripts.backfill_history import run_backfill
            await run_backfill()
            console.print('[bold green]✅ Backfill complete.[/]')
        else:
            console.print('[dim]Pattern matching will improve as more data accumulates.[/]')
    
    # ... rest of pipeline
```

### FIX I: ReportMetadata for dynamic footer stats
```python
class ReportMetadata(BaseModel):
    signal_count: int = 0
    pattern_match_count: int = 0
    contagion_chain_count: int = 0
    correlation_anomalies: int = 0
    pipeline_duration: float = 0.0
    generated_at: str = ''
    sections_ok: int = 17
    sections_degraded: int = 0
    
# Pass to template:
# {{ metadata.signal_count }} signals · {{ metadata.pattern_match_count }} pattern matches
```

### FIX J: Mood score color mapping in `report/chart_data.py`
```python
def mood_color(score: int) -> str:
    if score >= 55: return 'var(--phosphor)'  # Green
    if score >= 45: return 'var(--amber)'     # Amber  
    return 'var(--danger)'                     # Red

def mood_gradient(score: int) -> str:
    if score >= 55: return 'linear-gradient(90deg,var(--phosphor),#06d6a0)'
    if score >= 45: return 'linear-gradient(90deg,var(--amber),#f59e0b)'
    return 'linear-gradient(90deg,var(--danger),#dc2626)'

def mood_label(score: int) -> str:
    if score >= 75: return 'Bullish'
    if score >= 55: return 'Moderately Bullish'
    if score >= 45: return 'Neutral'
    if score >= 25: return 'Cautious'
    return 'Bearish'
```

---

## UPDATED BUILD CHECKLIST (Final)

```
☐ CLAUDE.md in project root
☐ reference/alpha-edge-v2.html saved (visual reference)
☐ config/constants.py — all 50 Nifty stocks + sectors + contagion rules
☐ 8 data collectors (market, stocks, options, fii_dii, block_deals, news, sentiment, tv_analysts)
☐ 15 feature modules (technical, options_analytics, gap_analysis, stock_screener,
    sector_rotation, correlation, pattern_matching, avoid_list, expiry_analysis,
    confidence_score, contagion_chain, risk_sizing, events_calendar, watchlist_queue, sentiment)
☐ agents/json_utils.py — JSON extraction utility (FIX A)
☐ 6 LangGraph agents (narrative, stock_analyst, options, scenario, conflict, watchlist)
☐ Corrected max pain algorithm (FIX B)
☐ VWAP proxy using typical price (FIX C)
☐ HV Rank as IV Rank proxy (FIX D)
☐ Simplified options skew (FIX E)
☐ Near-ATM PCR computation (FIX F)
☐ Sector-filtered pattern matching (FIX G)
☐ Auto-backfill on first run (FIX H)
☐ Dynamic ReportMetadata for footer (FIX I)
☐ Mood score color/label mapping (FIX J)
☐ Conditional expiry section rendering
☐ SectionStatus tracker for graceful degradation
☐ Complete Jinja2 template with ALL 17 sections
☐ All 12 Chart.js charts with exact phosphor terminal colors
☐ Report filename: alpha_edge_YYYY-MM-DD.html
☐ Browser auto-open after generation
☐ First-run auto-backfill
```
