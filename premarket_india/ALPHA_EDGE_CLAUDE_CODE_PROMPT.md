# ALPHA EDGE — Claude Code Build Prompt
## Pre-Market Intelligence Report Generator for Indian Day Traders

---

> **INSTRUCTIONS FOR CLAUDE CODE**: This is a complete engineering specification. Build the entire system described below. Follow the directory structure exactly. Implement every file. The output report must visually match the reference HTML template provided. Ask clarifying questions ONLY if something is technically ambiguous — otherwise, make the best engineering decision and keep building.

> **IMPORTANT — FIRST FILE TO CREATE**: Before building anything else, create `CLAUDE.md` in the project root using the companion CLAUDE.md file provided. This gives you persistent project context across sessions. Then create the directory structure and proceed with the build.

---

## 1. PROJECT OVERVIEW

Build **Alpha Edge** — an agentic AI system that generates a comprehensive pre-market trading intelligence report for Indian stock market (NSE/BSE) day traders. The system runs as a local cron job every trading day at 7:00 AM IST, collects data from free APIs, computes technical features, uses LangGraph to orchestrate AI agents for narrative generation, and outputs a beautiful self-contained HTML report (with an optional PDF export).

### Core Architecture Principle
**THE LLM NEVER GENERATES NUMBERS.** Every price, level, percentage, pattern match statistic, and flow figure is computed by deterministic Python code (Pandas/NumPy). The LLM (Groq Llama 3.3 70B) ONLY generates narrative text around pre-computed structured data. This prevents hallucination of financial data.

### Target Output
The generated report must have 17 sections matching this exact visual design:
- Dark "phosphor terminal" theme (navy/dark blue background, green accent)
- IBM Plex Mono + Instrument Serif + Libre Franklin fonts (via Google Fonts CDN)
- Chart.js interactive charts embedded in the HTML
- Sticky header with live market mood pills
- Each section in a card with numbered headers
- The report is a SINGLE self-contained HTML file (no external dependencies except Google Fonts CDN and Chart.js CDN)

---

## 2. TECH STACK (Use exactly these)

```
# Core
Python 3.11+
FastAPI                    # API layer (for future webhook/dashboard use)
LangGraph                  # Agent orchestration (parallel fan-out)
LangChain                  # LLM abstraction layer
langchain-groq             # Groq LLM provider
Groq API (free tier)       # Llama 3.3 70B — narrative generation

# Data Collection
yfinance                   # Market data (SGX Nifty proxy, Dow, Brent, USD/INR, Indian stocks)
nsetools                   # NSE stock data, options chain
nsepython                  # Advanced NSE data (FII/DII, OI data)
jugaad-data                # NSE historical bhavcopy, bulk/block deals
requests + beautifulsoup4  # Web scraping fallbacks
feedparser                 # RSS news feeds
tweepy                     # Twitter/X sentiment (optional, needs API key)
httpx                      # Async HTTP client

# Feature Engineering
pandas                     # Data manipulation
numpy                      # Numerical computation
pandas-ta                  # Technical indicators (RSI, ATR, pivot points, VWAP)
scipy                      # Correlation matrix, statistical functions
scikit-learn               # Clustering for pattern matching (KNN, cosine similarity)

# Report Generation
jinja2                     # HTML template engine
weasyprint                 # HTML → PDF conversion (optional)

# Storage
sqlite3                    # Local database for historical data + pattern fingerprints
                           # (upgrade path: TimescaleDB + Qdrant later)

# Scheduling
schedule                   # Python-based cron (local)
python-crontab             # System cron setup helper

# Config & Utils
pydantic                   # Data models + settings
pydantic-settings          # Environment variable management
python-dotenv              # .env file loading
loguru                     # Structured logging
tenacity                   # Retry logic for API calls
rich                       # Beautiful CLI output during pipeline execution
```

---

## 3. DIRECTORY STRUCTURE (Create exactly this)

```
alpha-edge/
├── .env.example                    # Template for API keys
├── .env                            # Actual keys (gitignored)
├── .gitignore
├── README.md
├── pyproject.toml                  # Project config (use poetry or pip)
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Pydantic Settings (all env vars)
│   └── constants.py                # Trading constants, sector mappings, etc.
│
├── data/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseCollector ABC with retry/fallback
│   │   ├── market_data.py          # SGX Nifty, Dow, Brent, USD/INR, VIX (yfinance)
│   │   ├── nse_stocks.py           # Indian stock prices, volumes (nsetools/yfinance)
│   │   ├── options_chain.py        # NSE options chain, OI data (nsepython)
│   │   ├── fii_dii.py              # FII/DII flow data (nsepython + scraper)
│   │   ├── block_deals.py          # Block/bulk deal data (jugaad-data + scraper)
│   │   ├── news.py                 # RSS feeds (Reuters, Moneycontrol, ET, Livemint)
│   │   └── social_sentiment.py     # Twitter/X + Stocktwits (optional)
│   │
│   └── models.py                   # Pydantic models for raw collected data
│
├── features/
│   ├── __init__.py
│   ├── pipeline.py                 # Master feature pipeline orchestrator
│   ├── technical.py                # Pivot points, VWAP, ATR, RSI, Fibonacci
│   ├── options_analytics.py        # PCR, max pain, IV rank, unusual OI
│   ├── gap_analysis.py             # Gap size computation, historical fill rates
│   ├── sector_rotation.py          # Sector flow scoring and ranking
│   ├── correlation.py              # 20-day rolling correlation matrix + anomalies
│   ├── sentiment.py                # NLP sentiment scoring (keyword + VADER)
│   ├── risk_sizing.py              # Position sizing based on VIX + ATR
│   ├── confidence_score.py         # Ensemble AI market mood score (0-100)
│   ├── pattern_matching.py         # Historical pattern fingerprint + similarity search
│   ├── contagion_chain.py          # Sector/macro impact chain (rule-based graph)
│   └── models.py                   # ComputedFeatures Pydantic model
│
├── agents/
│   ├── __init__.py
│   ├── graph.py                    # LangGraph graph definition (fan-out/fan-in)
│   ├── state.py                    # Graph state model
│   ├── narrative_agent.py          # Market narrative "why" writer
│   ├── stock_analyst_agent.py      # Per-stock catalyst + timing commentary
│   ├── options_agent.py            # Options flow interpretation
│   ├── scenario_agent.py           # 3 if/then scenario playbooks
│   ├── conflict_agent.py           # TV call vs data conflict detection
│   ├── prompts/
│   │   ├── narrative.py            # System + user prompt templates
│   │   ├── stock_analyst.py
│   │   ├── options.py
│   │   ├── scenario.py
│   │   └── conflict.py
│   └── models.py                   # Agent output Pydantic models
│
├── report/
│   ├── __init__.py
│   ├── renderer.py                 # Jinja2 template renderer
│   ├── pdf_generator.py            # HTML → PDF (weasyprint)
│   ├── chart_data.py               # Prepare Chart.js JSON data
│   └── templates/
│       └── alpha_edge_report.html.j2   # The master Jinja2 template
│
├── storage/
│   ├── __init__.py
│   ├── database.py                 # SQLite setup, migrations
│   ├── historical.py               # Historical OHLCV storage & retrieval
│   └── pattern_store.py            # Pattern fingerprint storage & search
│
├── delivery/
│   ├── __init__.py
│   ├── email.py                    # Email delivery (Resend, future)
│   └── telegram.py                 # Telegram bot delivery (future)
│
├── api/
│   ├── __init__.py
│   └── main.py                     # FastAPI app (future dashboard API)
│
├── scripts/
│   ├── backfill_history.py         # One-time: backfill 2+ years of historical data
│   ├── setup_cron.py               # Setup local cron job
│   └── run_manual.py               # Manual trigger for testing
│
├── tests/
│   ├── __init__.py
│   ├── test_collectors.py
│   ├── test_features.py
│   ├── test_agents.py
│   └── test_renderer.py
│
├── output/                          # Generated reports land here
│   └── .gitkeep
│
└── main.py                          # ENTRY POINT — runs the full pipeline
```

---

## 4. CONFIGURATION

### `.env.example`
```env
# === LLM ===
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# === Data Sources ===
# Twitter (optional - skip if you don't have this)
TWITTER_BEARER_TOKEN=

# === Report Settings ===
REPORT_OUTPUT_DIR=./output
GENERATE_PDF=false

# === Trading Config ===
TRADING_CAPITAL=2400000          # ₹24 Lakhs base capital
MAX_RISK_PER_TRADE_PCT=1.0      # 1% of capital
MAX_DAILY_LOSS_PCT=2.5           # 2.5% daily limit
MAX_CONCURRENT_POSITIONS=3

# === Schedule ===
REPORT_TIME=07:00                # IST
MARKET_OPEN_TIME=09:15           # IST

# === Logging ===
LOG_LEVEL=INFO
```

### `config/settings.py`
Use Pydantic Settings to load all env vars with type validation and defaults.

### `config/constants.py`
This file must contain:
```python
# Nifty 50 stock list with sector mapping
NIFTY_50_STOCKS = {
    "RELIANCE": {"name": "Reliance Industries", "sector": "Oil & Gas", "weight": 10.2},
    "TCS": {"name": "Tata Consultancy Services", "sector": "IT", "weight": 4.1},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Banking", "weight": 8.8},
    "INFY": {"name": "Infosys", "sector": "IT", "weight": 5.6},
    "ICICIBANK": {"name": "ICICI Bank", "sector": "Banking", "weight": 6.2},
    "INDUSINDBK": {"name": "IndusInd Bank", "sector": "Banking", "weight": 1.1},
    "INDIGO": {"name": "InterGlobe Aviation", "sector": "Aviation", "weight": 0.8},
    "ASIANPAINT": {"name": "Asian Paints", "sector": "Paints", "weight": 1.2},
    "TRENT": {"name": "Trent Ltd", "sector": "Retail", "weight": 0.9},
    "BPCL": {"name": "Bharat Petroleum", "sector": "Oil & Gas", "weight": 0.5},
    "TATAMOTORS": {"name": "Tata Motors", "sector": "Auto", "weight": 2.1},
    "IRCTC": {"name": "IRCTC", "sector": "Tourism", "weight": 0.3},
    "ZOMATO": {"name": "Zomato", "sector": "Tech", "weight": 0.7},
    "ADANIENT": {"name": "Adani Enterprises", "sector": "Conglomerate", "weight": 1.0},
    # ... add all 50 stocks with accurate sector mappings
}

SECTORS = [
    "Banking", "IT", "Oil & Gas", "Auto", "Pharma", "FMCG",
    "Metals", "Paints", "Aviation", "Retail", "Telecom", "Infra"
]

# yfinance ticker mappings (NSE stocks need .NS suffix)
YFINANCE_TICKER_MAP = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFCBANK": "HDFCBANK.NS",
    # ... all stocks
    # Macro tickers:
    "SGX_NIFTY": "^NSEI",           # Use Nifty as proxy (SGX not available free)
    "DOW_FUTURES": "YM=F",          # Dow futures
    "BRENT_CRUDE": "BZ=F",          # Brent crude futures
    "USDINR": "USDINR=X",           # USD/INR
    "INDIA_VIX": "^INDIAVIX",       # India VIX
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}

# Contagion chain rules (used by contagion_chain.py)
CONTAGION_RULES = {
    "crude_down": {
        "1st_order": {
            "beneficiaries": ["Aviation", "Paints", "Auto", "Tyres"],
            "losers": ["Oil & Gas (OMCs)", "Oil & Gas (Upstream)"]
        },
        "2nd_order": {
            "beneficiaries": ["Logistics", "FMCG", "Chemicals"],
            "losers": ["Oil Services"]
        },
        "3rd_order": {
            "beneficiaries": ["RBI Rate Cut Probability", "Current Account", "FII EM Flows"],
            "neutral": ["Fiscal Deficit"]
        }
    },
    "crude_up": { ... },   # Reverse of crude_down
    "fed_dovish": { ... },  # EM positive, banking positive
    "fed_hawkish": { ... }, # EM negative
    "inr_weaken": { ... },  # IT positive, importers negative
    "inr_strengthen": { ... },
}

# Expiry calendar 2026 (monthly expiry dates - last Thursday of each month)
EXPIRY_DATES_2026 = [
    "2026-01-29", "2026-02-26", "2026-03-26", "2026-04-30",
    "2026-05-28", "2026-06-25", "2026-07-30", "2026-08-27",
    "2026-09-24", "2026-10-29", "2026-11-26", "2026-12-31"
]

# TV Analyst database (for sentiment conflict detection)
TV_ANALYSTS = {
    "Sudarshan Sukhani": {"channel": "CNBC-TV18", "accuracy_30d": 0.61},
    "Prakash Gaba": {"channel": "CNBC Awaaz", "accuracy_30d": 0.54},
    "Kunal Bothra": {"channel": "CNBC-TV18", "accuracy_30d": 0.58},
    "Rajat Bose": {"channel": "ET Now", "accuracy_30d": 0.48},
}
```

---

## 5. DATA COLLECTORS — Detailed Implementation Specs

### `data/collectors/base.py`
```python
# Implement an abstract BaseCollector with:
# - async collect() method
# - tenacity retry (3 retries, exponential backoff)
# - fallback_collector chain
# - provenance tagging (every value gets: source, timestamp, fresh bool)
# - timeout (30 seconds default)
# - structured logging via loguru
```

### `data/collectors/market_data.py` — MarketDataCollector
```
Uses: yfinance
Collects:
  - SGX Nifty: Use ^NSEI (Nifty 50 index) as proxy since free SGX data unavailable.
    For pre-market, fetch the PREVIOUS close and compute expected open from
    Dow futures overnight movement + Brent crude change + USD/INR change
    using a simple linear regression model:
    expected_nifty_open = prev_close * (1 + 0.4*dow_pct + 0.15*(-brent_pct) + 0.1*(-usdinr_pct))
  - Dow Futures (YM=F): Latest price + % change
  - Brent Crude (BZ=F): Latest price + % change
  - USD/INR (USDINR=X): Latest price + % change
  - India VIX (^INDIAVIX): Latest close + % change
  - Nifty historical (last 30 days OHLCV for technical indicators)
  - BankNifty historical (last 30 days OHLCV)

Return: MacroData pydantic model with all values + sparkline data (last 10 closes)
```

### `data/collectors/nse_stocks.py` — NSEStockCollector
```
Uses: yfinance (batch download for all Nifty 50 stocks)
Collects:
  - Previous day OHLCV for all Nifty 50 stocks
  - Pre-market expected gap: Use overnight global cues to estimate gap direction
    Simple model: sector_sensitivity * crude_change + market_beta * dow_change
  - 20-day volume average for each stock
  - Delivery percentage (if available from nsetools, else estimate)

Key optimization: Use yfinance.download() with tickers list for batch API call.
Do NOT call one stock at a time — that's 50 API calls vs 1.

Return: List[StockData] pydantic models
```

### `data/collectors/options_chain.py` — OptionsChainCollector
```
Uses: nsepython (nse_optionchain_scrapper function)
Collects:
  - Nifty options chain (all strikes, CE + PE)
  - BankNifty options chain
  - Top 10 gap-up stock options chains
  - For each: OI, change in OI, volume, IV, LTP

Compute from raw chain:
  - PCR (put OI / call OI)
  - Max Pain (strike where total premium payout to option writers is minimum)
  - IV Rank (current IV vs 52-week IV range, percentile)
  - Unusual OI (strikes where volume > 3x 20-day average)

IMPORTANT: NSE website rate limits aggressively. Add 1-2 second delays between
requests. Use headers to mimic browser. If nsepython fails, fall back to
manually scraping from https://www.nseindia.com/option-chain with beautifulsoup4.

Return: OptionsAnalyticsData pydantic model
```

### `data/collectors/fii_dii.py` — FIIDIICollector
```
Uses: nsepython (fii_data function) OR web scraper
Collects:
  - FII net buy/sell (cash segment) — previous day
  - DII net buy/sell (cash segment) — previous day
  - FII index futures OI + net position
  - FII index options net position
  - 5-day rolling totals for trend

Sources (in priority order):
  1. nsepython fii_data()
  2. Scrape from https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/
  3. Scrape from NSDL website
  4. Fallback: use previous day cached data with "stale" flag

Return: FIIDIIData pydantic model
```

### `data/collectors/block_deals.py` — BlockDealCollector
```
Uses: jugaad-data OR BSE announcements scraper
Collects:
  - Block deals from previous trading day
  - Bulk deals from previous trading day
  - For each: stock, quantity, price, buyer/seller name (if available)

Sources:
  1. jugaad_data.nse.block_deals(date)
  2. Scrape BSE announcements page
  3. Scrape Moneycontrol block deals page

Return: List[BlockDeal] pydantic models
```

### `data/collectors/news.py` — NewsCollector
```
Uses: feedparser (RSS)
Collects headlines from:
  - https://www.moneycontrol.com/rss/latestnews.xml
  - https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms
  - https://www.livemint.com/rss/markets
  - Reuters India business (find current RSS URL)

For each headline: title, source, published time, URL.
Filter: only last 12 hours of headlines.
Classify: Use keyword matching to tag each headline with relevant tickers/sectors.

Return: List[NewsItem] pydantic models
```

### `data/collectors/social_sentiment.py` — SocialSentimentCollector
```
PHASE 1 (no Twitter API): Use a keyword-based approach:
  - Scrape Stocktwits API (free, no auth needed): https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json
  - Count bullish vs bearish tagged messages
  - Compute sentiment score per ticker

PHASE 2 (with Twitter API): Use tweepy to search for #INDIGO, #NIFTY, etc.
  - VADER sentiment analysis on each tweet
  - Volume-weighted sentiment score

If no API keys available, generate realistic simulated sentiment data
with a disclaimer in the report.

Return: List[SentimentData] pydantic models
```

---

## 6. FEATURE ENGINEERING — Detailed Specs

### `features/technical.py`
```
Input: 30-day OHLCV for Nifty, BankNifty, individual stocks
Output: TechnicalLevels model per instrument

Compute using pandas-ta library:
  - Classic Pivot Points: PP = (H+L+C)/3, R1/S1, R2/S2, R3/S3
  - Fibonacci Extension: 0.618, 1.0, 1.618 from previous swing
  - VWAP: Volume-weighted average price (previous session)
  - ATR(14): Average True Range
  - RSI(14): Relative Strength Index
  - 20-DMA, 50-DMA, 200-DMA: Moving averages
  - Bollinger Bands: 20-period, 2 std dev
```

### `features/options_analytics.py`
```
Input: Raw options chain data
Output: OptionsAnalytics model

Compute:
  - PCR = Total Put OI / Total Call OI
  - Max Pain = Strike with minimum total payout
    Algorithm: For each strike, calculate:
      call_payout = sum of max(0, strike - S) * call_OI for all calls
      put_payout = sum of max(0, S - strike) * put_OI for all puts
      total_payout = call_payout + put_payout
    Max pain = strike with minimum total_payout

  - IV Rank = (current_iv - 52wk_low_iv) / (52wk_high_iv - 52wk_low_iv) * 100
  - Unusual Activity: Flag strikes where volume > 3x 20-day avg volume
  - Options Skew: (25-delta call IV - 25-delta put IV) / ATM IV
  - Theta decay estimate: Use Black-Scholes approximation
```

### `features/gap_analysis.py`
```
Input: Expected open, previous close, historical gap data from SQLite
Output: GapStatistics model

Compute:
  - Expected gap % = (expected_open - prev_close) / prev_close * 100
  - Gap category: Small (<0.3%), Medium (0.3-1.0%), Large (1.0-1.5%), Mega (>1.5%)
  - Historical fill rate by category (from stored historical data)
  - Expiry week adjustment factor (from stored data)
  - VIX regime adjustment (VIX < 15 = low, 15-20 = medium, > 20 = high)
  - Final sustainability probability = base_rate * vix_adj * expiry_adj
```

### `features/pattern_matching.py` — THIS IS THE KEY DIFFERENTIATOR
```
Input: Today's market conditions (gap size, crude change, VIX, sector, day of week, etc.)
Output: List[PatternMatch] with historical win rates and outcome stats

Algorithm:
1. Encode today's conditions as a feature vector (15 dimensions):
   [gap_pct, crude_change, vix_level, vix_change, fii_flow_bucket,
    pcr, day_of_week, is_expiry_week, days_to_expiry, prev_5d_return,
    rsi_14, volume_ratio, sector_encoded, gap_direction, market_cap_bucket]

2. Normalize all features to 0-1 range using stored min/max from history.

3. Use scikit-learn NearestNeighbors (cosine similarity) to find top-20
   most similar historical sessions from SQLite pattern store.

4. Compute outcome statistics:
   - win_rate = count(closed_above_open) / total_matches
   - median_upside = median(intraday_return where return > 0)
   - median_drawdown = median(max_drawdown_from_open)
   - typical_timing = mode(time_of_high buckets)

5. Return as PatternMatch pydantic model with all stats.

For MVP: If historical data is limited (<200 sessions), use wider similarity
threshold. Clearly state "N similar events found" in the report.
```

### `features/contagion_chain.py`
```
Input: Today's dominant catalyst (e.g., "crude_down")
Output: ContagionChain with 1st/2nd/3rd order effects

This is RULE-BASED, not LLM-generated. Use CONTAGION_RULES from constants.py.
Look at today's top macro movers, determine the dominant catalyst:
  - If abs(crude_change) > 1.0%: catalyst = "crude_down" or "crude_up"
  - If abs(usdinr_change) > 0.3%: catalyst = "inr_weaken" or "inr_strengthen"
  - If specific news about Fed/RBI: catalyst = "fed_dovish" or "rbi_cut"

Return structured ContagionChain with specific stock/sector names per order.
```

### `features/confidence_score.py`
```
Input: All computed features
Output: Integer 0-100 (AI Market Mood Score)

Weighted ensemble of 12 sub-signals:
  sgx_direction    = +1 if gap_up, -1 if gap_down, weight 0.15
  vix_direction    = +1 if vix_falling, -1 if rising, weight 0.12
  pcr_signal       = +1 if PCR > 1.0, -1 if < 0.8, weight 0.10
  fii_flow         = +1 if net positive, -1 if negative, weight 0.10
  dii_flow         = +1 if positive, weight 0.08
  crude_for_india  = +1 if crude falling (good for India), weight 0.10
  dow_direction    = +1 if positive, weight 0.08
  sector_breadth   = count(positive sectors) / total, weight 0.08
  news_sentiment   = avg sentiment score, weight 0.06
  social_sentiment = avg social score, weight 0.05
  expiry_adj       = -0.1 if expiry week (adds caution), weight 0.05
  rsi_signal       = -1 if RSI > 75 (overbought caution), weight 0.03

  raw_score = sum(signal * weight) → normalized to 0-100 range
  Labels: 0-25 Bearish, 25-45 Cautious, 45-55 Neutral, 55-75 Moderately Bullish, 75-100 Bullish
```

---

## 7. LANGGRAPH AGENT ORCHESTRATION

### `agents/graph.py` — The Heart of the System
```
Build a LangGraph StateGraph with this topology:

                    ┌─ narrative_agent ──┐
                    ├─ stock_analyst ────┤
  computed_data ──→ ├─ options_agent ────┤ ──→ merge_outputs ──→ ReportPayload
                    ├─ scenario_agent ───┤
                    └─ conflict_agent ───┘

All 5 agents run in PARALLEL (fan-out) and merge into a single state (fan-in).

State Model (agents/state.py):
  class AgentState(TypedDict):
      computed_features: ComputedFeatures   # Input from feature pipeline
      narrative: Optional[NarrativeOutput]
      stock_analyses: Optional[List[StockAnalysis]]
      options_summary: Optional[str]
      scenario_playbook: Optional[ScenarioPlaybook]
      conflict_flags: Optional[List[ConflictFlag]]

Use langchain_groq.ChatGroq as the LLM:
  model = ChatGroq(
      model="llama-3.3-70b-versatile",
      temperature=0.3,        # Low temp for factual financial writing
      max_tokens=1024,
      api_key=settings.GROQ_API_KEY,
  )

IMPORTANT: Groq free tier has rate limits (30 requests/min, 14,400 tokens/min).
Add delays between agent calls if hitting limits. Consider sequential fallback
if parallel exceeds rate limit.
```

### Agent Prompts — Critical for Quality

Each agent gets a SYSTEM PROMPT and a USER PROMPT. The system prompt defines the agent's persona and constraints. The user prompt injects the computed data.

#### `agents/prompts/narrative.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Market Narrative Writer — an experienced financial journalist 
who writes pre-market briefings for professional Indian day traders.

RULES:
1. NEVER invent or estimate any number. Every statistic, price, percentage, and level 
   in your narrative MUST come from the data provided below. If a number is not in the data, 
   DO NOT mention it.
2. Write in a direct, authoritative tone. No hedging with "might" or "could" — be opinionated.
3. Lead with the dominant theme of the day (the biggest catalyst).
4. Connect macro events to specific sector/stock impacts.
5. Include historical context when the data provides pattern matches.
6. Mention expiry week dynamics if applicable.
7. Keep it to 4-5 paragraphs + 4 bullet points maximum.
8. Use specific tickers (INDIGO, not "airline stocks").
9. Output as JSON with keys: headline (str), body (str), bullets (list of {icon, text}).
   icon must be one of: "M" (macro), "F" (flow), "R" (risk), "E" (event).
"""

USER_PROMPT_TEMPLATE = """Generate the market narrative based on this pre-computed data:

MACRO DATA:
{macro_json}

SECTOR FLOWS:
{sector_flows_json}

TOP GAP-UP CANDIDATES:
{gap_up_json}

OPTIONS SUMMARY:
{options_json}

CONTAGION CHAIN:
{contagion_json}

NEWS HEADLINES (last 12h):
{news_json}

TODAY'S DATE: {date}
IS EXPIRY WEEK: {is_expiry_week}
DAYS TO EXPIRY: {days_to_expiry}
MARKET MOOD SCORE: {confidence_score}/100

Write the narrative now. Output ONLY valid JSON."""
```

#### `agents/prompts/stock_analyst.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Stock Analyst Agent. For each gap-up candidate, 
you write a concise catalyst analysis and timing recommendation.

RULES:
1. NEVER invent prices, levels, or percentages. Only use data provided.
2. For each stock, provide: catalyst (why it's gapping), timing_pattern (when to enter).
3. Reference the pattern match data to give historical context.
4. Be specific: "enter at ₹4,580 on VWAP retest" not "buy on dips".
5. Warn about risks specific to each setup.
6. Output as JSON: list of {ticker, catalyst_text, timing_text} objects.
"""
```

#### `agents/prompts/scenario.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Scenario Planner. Based on pre-computed market data,
you create exactly 3 intraday scenarios with specific if/then action plans.

RULES:
1. Scenario A = Bull case (highest probability if data is bullish)
2. Scenario B = Range-bound / choppy
3. Scenario C = Bear case / gap-and-trap
4. Each scenario must have: trigger condition, probability (must sum to 100%), 
   specific actions (with real levels from the data), and exit rules.
5. NEVER invent price levels. Only use levels from the data provided.
6. Output as JSON: list of 3 {label, probability, trigger, actions, exit} objects.
"""
```

#### `agents/prompts/options.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Options Flow Interpreter. You analyze unusual 
options activity and explain what smart money is doing.

RULES:
1. Interpret the unusual OI data provided — explain whether each signal is 
   bullish, bearish, or hedging.
2. Look for contradictions: e.g., cash selling + call buying = hedging not bearish.
3. Highlight the most significant flow (highest volume/avg ratio).
4. Keep it to 3-4 sentences. Be direct.
5. Output as JSON: {summary: str}
"""
```

#### `agents/prompts/conflict.py`
```python
SYSTEM_PROMPT = """You are Alpha Edge's Conflict Detection Agent. You compare TV analyst 
calls against the actual data to flag contradictions.

RULES:
1. For each TV analyst call provided, check if it contradicts the data:
   - Bullish call on a stock with bearish options flow?
   - Short recommendation when PCR is bullish?
   - Buy recommendation when RSI > 75 (overbought)?
2. Flag ONLY genuine conflicts. Not every disagreement is a conflict.
3. Output as JSON: list of {analyst, call, conflict_reason} objects. 
   Empty list if no conflicts found.
"""
```

---

## 8. REPORT RENDERER — Jinja2 Template

### `report/templates/alpha_edge_report.html.j2`

This is the MOST IMPORTANT file. It must produce HTML that EXACTLY matches the visual design 
of the reference report (alpha-edge-v2.html). 

The template must:
1. Use the EXACT same CSS from the reference (phosphor terminal theme, IBM Plex Mono, etc.)
2. Inject ALL numerical data from ComputedFeatures via Jinja2 variables
3. Inject ALL narrative text from AgentNarratives via Jinja2 variables
4. Generate Chart.js data as inline JSON from chart_data.py output
5. Be a single self-contained HTML file (CSS inline, JS inline, only external = Google Fonts + Chart.js CDN)

Template variables available:
```
{{ report_date }}                    # "Monday, 30 March 2026"
{{ generated_at }}                   # "07:18 IST"
{{ confidence_score }}               # 72
{{ confidence_label }}               # "Moderately Bullish"

{# Macro Dashboard #}
{{ macro.sgx_nifty.value }}          # 23542
{{ macro.sgx_nifty.change }}         # +158.4
{{ macro.sgx_nifty.change_pct }}     # +0.68
{{ macro.sgx_nifty.sparkline }}      # [23180, 23220, ...] (last 10)
{{ macro.dow_futures.value }}        # etc.
{{ macro.brent_crude.value }}
{{ macro.usdinr.value }}
{{ macro.india_vix.value }}
{{ macro.fii_net.value }}

{# Narrative (from AI agent) #}
{{ narrative.headline }}
{{ narrative.body }}
{% for b in narrative.bullets %}
  {{ b.icon }} {{ b.text }}
{% endfor %}

{# Technical Levels #}
{{ nifty_levels.r3 }}
{{ nifty_levels.r2 }}
... etc for all levels

{# Gap-Up Setups #}
{% for stock in gap_up_stocks %}
  {{ stock.rank }}
  {{ stock.ticker }}
  {{ stock.company }}
  {{ stock.sector }}
  {{ stock.gap_pct }}
  {{ stock.catalyst_text }}         # From AI agent
  {{ stock.timing_text }}           # From AI agent  
  {{ stock.options_skew }}
  {{ stock.iv_rank }}
  {{ stock.entry_zone }}
  {{ stock.targets }}               # [T1, T2, T3]
  {{ stock.stop_loss }}
  {{ stock.pattern_match.count }}   # "18 similar events"
  {{ stock.pattern_match.win_rate }}
  {{ stock.pattern_match.median_upside }}
  {{ stock.pattern_match.median_drawdown }}
{% endfor %}

{# ... similar for all 17 sections #}

{# Chart Data (JSON) #}
{{ sector_chart_data | tojson }}
{{ contagion_chart_data | tojson }}
{{ oi_chart_data | tojson }}
{{ fii_dii_chart_data | tojson }}
{{ gap_size_chart_data | tojson }}
{{ gap_expiry_chart_data | tojson }}
{{ correlation_matrix | tojson }}
```

CRITICAL: Copy the EXACT CSS from the reference report. The classes, colors, fonts, 
layout, hover effects — everything must match. The only change is that hardcoded 
values become Jinja2 template variables.

---

## 9. MAIN PIPELINE — Entry Point

### `main.py`
```python
"""
Alpha Edge — Pre-Market Intelligence Pipeline
Runs daily at 07:00 IST. Generates report by 07:18 IST.
"""
import asyncio
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import settings
from data.collectors.market_data import MarketDataCollector
from data.collectors.nse_stocks import NSEStockCollector
from data.collectors.options_chain import OptionsChainCollector
from data.collectors.fii_dii import FIIDIICollector
from data.collectors.block_deals import BlockDealCollector
from data.collectors.news import NewsCollector
from data.collectors.social_sentiment import SocialSentimentCollector
from features.pipeline import FeaturePipeline
from agents.graph import run_agent_graph
from report.renderer import ReportRenderer
from report.chart_data import prepare_chart_data
from storage.database import init_db, store_daily_snapshot

console = Console()

async def run_pipeline():
    """Full pipeline: Ingest → Compute → AI → Render → Deliver"""
    start = datetime.now()
    logger.info(f"🚀 Alpha Edge Pipeline Started at {start.strftime('%H:%M:%S IST')}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        console=console
    ) as progress:
    
        # ── STAGE 1: Data Ingestion (parallel) ──
        task = progress.add_task("📡 Collecting market data...", total=None)
        raw_data = await collect_all_data()
        progress.update(task, description="✅ Data collected")
        
        # ── STAGE 2: Feature Engineering ──
        task = progress.add_task("🔬 Computing features...", total=None)
        features = FeaturePipeline().compute(raw_data)
        progress.update(task, description="✅ Features computed")
        
        # ── STAGE 3: Store snapshot (for future pattern matching) ──
        task = progress.add_task("💾 Storing snapshot...", total=None)
        store_daily_snapshot(features)
        progress.update(task, description="✅ Snapshot stored")
        
        # ── STAGE 4: AI Agent Orchestration ──
        task = progress.add_task("🧠 AI agents generating narratives...", total=None)
        narratives = await run_agent_graph(features)
        progress.update(task, description="✅ Narratives generated")
        
        # ── STAGE 5: Report Rendering ──
        task = progress.add_task("📄 Rendering report...", total=None)
        chart_data = prepare_chart_data(features)
        renderer = ReportRenderer()
        html_report = renderer.render(features, narratives, chart_data)
        report_path = renderer.save(html_report)
        progress.update(task, description=f"✅ Report saved: {report_path}")
        
        # ── STAGE 6: Optional PDF ──
        if settings.GENERATE_PDF:
            task = progress.add_task("📑 Generating PDF...", total=None)
            from report.pdf_generator import generate_pdf
            pdf_path = generate_pdf(report_path)
            progress.update(task, description=f"✅ PDF saved: {pdf_path}")
    
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"✅ Pipeline complete in {elapsed:.1f}s")
    console.print(f"\n[bold green]✅ Report ready: {report_path}[/]")
    console.print(f"[dim]Pipeline completed in {elapsed:.1f} seconds[/]")

async def collect_all_data():
    """Run all collectors in parallel with fallback handling"""
    results = await asyncio.gather(
        MarketDataCollector().collect(),
        NSEStockCollector().collect(),
        OptionsChainCollector().collect(),
        FIIDIICollector().collect(),
        BlockDealCollector().collect(),
        NewsCollector().collect(),
        SocialSentimentCollector().collect(),
        return_exceptions=True
    )
    # Handle individual collector failures gracefully
    # Log warnings for failed collectors, use cached/default data
    return aggregate_results(results)

if __name__ == "__main__":
    init_db()  # Ensure SQLite tables exist
    asyncio.run(run_pipeline())
```

---

## 10. SQLITE SCHEMA (storage/database.py)

```sql
-- Historical daily OHLCV for all tracked stocks
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    delivery_pct REAL,
    UNIQUE(ticker, date)
);

-- Pattern fingerprints for similarity search
CREATE TABLE IF NOT EXISTS session_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    -- Feature vector components:
    gap_pct REAL,
    crude_change REAL,
    vix_level REAL,
    vix_change REAL,
    fii_flow_bucket INTEGER,
    pcr REAL,
    day_of_week INTEGER,
    is_expiry_week BOOLEAN,
    days_to_expiry INTEGER,
    prev_5d_return REAL,
    rsi_14 REAL,
    volume_ratio REAL,
    sector TEXT,
    -- Outcome (filled at EOD):
    closed_above_open BOOLEAN,
    intraday_return REAL,
    max_drawdown_from_open REAL,
    time_of_high_minutes INTEGER,
    UNIQUE(ticker, date)
);

-- FII/DII daily flows
CREATE TABLE IF NOT EXISTS fii_dii_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    fii_cash_net REAL,
    dii_cash_net REAL,
    fii_futures_net REAL,
    fii_options_net REAL
);

-- Generated report log
CREATE TABLE IF NOT EXISTS report_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    generated_at TIMESTAMP,
    pipeline_duration_seconds REAL,
    confidence_score INTEGER,
    report_path TEXT,
    status TEXT  -- 'success', 'partial', 'failed'
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON daily_ohlcv(ticker, date);
CREATE INDEX IF NOT EXISTS idx_fingerprint_ticker ON session_fingerprints(ticker);
CREATE INDEX IF NOT EXISTS idx_fingerprint_date ON session_fingerprints(date);
```

---

## 11. BACKFILL SCRIPT (scripts/backfill_history.py)

```
This script runs ONCE to populate the SQLite database with 2+ years of historical data.

Uses yfinance to download:
  - All Nifty 50 stocks: daily OHLCV from 2024-01-01 to today
  - Nifty, BankNifty: daily OHLCV
  - India VIX: daily close
  - Brent Crude: daily close
  - USD/INR: daily close
  - FII/DII flows (from jugaad-data or NSE archives)

After downloading, compute and store session fingerprints for all historical dates.
This populates the pattern matching engine.

IMPORTANT: yfinance has rate limits. Add delays. Download in batches of 10 stocks.
This script will take 5-10 minutes to run. Show progress bar with rich.
```

---

## 12. SCHEDULING (scripts/setup_cron.py)

```python
# For local cron setup on Mac/Linux:
# Add this to crontab: 0 7 * * 1-5 cd /path/to/alpha-edge && python main.py
# (Runs at 7:00 AM, Monday through Friday)

# The script should:
# 1. Check if it's a trading day (not weekend, not Indian market holiday)
# 2. If not trading day, exit silently
# 3. If trading day, run the pipeline
# 4. On completion, open the HTML report in default browser

# Indian market holidays 2026 (approximate - verify):
MARKET_HOLIDAYS_2026 = [
    "2026-01-26",  # Republic Day
    "2026-03-10",  # Maha Shivaratri
    "2026-03-17",  # Holi
    "2026-04-02",  # Ram Navami
    "2026-04-14",  # Ambedkar Jayanti
    "2026-04-18",  # Good Friday
    # ... add all NSE holidays
]
```

---

## 13. TESTING PRIORITIES

Build tests in this order:
1. `test_collectors.py`: Mock API responses, verify parsing. Most critical.
2. `test_features.py`: Test technical level computation with known inputs.
3. `test_agents.py`: Test with sample ComputedFeatures, verify JSON output parsing.
4. `test_renderer.py`: Test Jinja2 template renders without errors.

For each test, create fixture data files in `tests/fixtures/` with realistic sample data.

---

## 14. BUILD SEQUENCE — Follow this exact order

```
PHASE 1: Foundation (Day 1-2)
  ☐ Create directory structure
  ☐ Set up pyproject.toml / requirements.txt
  ☐ Implement config/settings.py and config/constants.py
  ☐ Implement storage/database.py (SQLite schema)
  ☐ Create all Pydantic models (data/models.py, features/models.py, agents/models.py)

PHASE 2: Data Collection (Day 3-5)
  ☐ Implement base.py collector with retry logic
  ☐ Implement market_data.py (yfinance — this is the easiest, start here)
  ☐ Implement nse_stocks.py (yfinance batch download)
  ☐ Implement news.py (RSS feeds)
  ☐ Implement fii_dii.py (scraper with fallback)
  ☐ Implement options_chain.py (nsepython — most fragile, handle errors carefully)
  ☐ Implement block_deals.py
  ☐ Implement social_sentiment.py (Stocktwits or simulated)
  ☐ Run backfill_history.py to populate SQLite

PHASE 3: Feature Engineering (Day 6-8)
  ☐ Implement technical.py (pivot points, RSI, ATR, VWAP)
  ☐ Implement gap_analysis.py
  ☐ Implement options_analytics.py (PCR, max pain, IV rank)
  ☐ Implement sector_rotation.py
  ☐ Implement correlation.py
  ☐ Implement confidence_score.py
  ☐ Implement pattern_matching.py (KNN on SQLite fingerprints)
  ☐ Implement contagion_chain.py (rule-based)
  ☐ Implement risk_sizing.py
  ☐ Implement pipeline.py (orchestrator)

PHASE 4: AI Agents (Day 9-11)
  ☐ Set up langchain-groq integration
  ☐ Implement all 5 agent prompt files
  ☐ Implement each agent module with structured output parsing
  ☐ Implement graph.py (LangGraph StateGraph with fan-out)
  ☐ Test agents individually, then together
  ☐ Handle Groq rate limits gracefully (add delays, retry)

PHASE 5: Report Rendering (Day 12-14)
  ☐ Convert alpha-edge-v2.html reference into Jinja2 template
  ☐ Implement chart_data.py (prepare Chart.js JSON)
  ☐ Implement renderer.py
  ☐ Implement pdf_generator.py (optional)
  ☐ Test full pipeline end-to-end

PHASE 6: Polish & Deploy (Day 15+)
  ☐ Wire up main.py
  ☐ Set up local cron job
  ☐ Add error handling, alerting
  ☐ Run for 5 trading days, fix bugs
  ☐ Start building real pattern match history
```

---

## 15. CRITICAL IMPLEMENTATION NOTES

### Groq Rate Limits (Free Tier)
- 30 requests per minute
- ~6,000 tokens per minute (varies)
- 14,400 requests per day
- Strategy: Run agents sequentially with 2-second delays if parallel hits limits.
  Sequential is fine — total LLM time will be ~30 seconds, well within budget.

### NSE Data Scraping Pitfalls
- NSE website blocks automated requests aggressively
- Always set User-Agent headers to mimic a real browser
- nsepython handles most of this, but it can break when NSE changes their API
- ALWAYS have a fallback (yfinance for stock data, moneycontrol scraper for FII/DII)

### yfinance Reliability
- Pre-market data for Indian stocks is NOT available via yfinance
- Use yfinance ONLY for: previous day close/OHLCV, Dow futures, Brent crude, USD/INR
- For "expected open" calculation, use the regression model described in market_data.py spec

### Timezone Handling
- ALWAYS use IST (Asia/Kolkata) for all timestamps
- yfinance returns data in exchange timezone (IST for .NS stocks, US ET for futures)
- Normalize everything to IST in the collectors

### Error Handling Philosophy
- If a data source fails, the report STILL generates with available data
- Missing sections show a subtle "⚠ Data unavailable" message
- The pipeline should NEVER crash completely — use try/except at every stage
- Log all errors for debugging, but keep the report flowing

---

## 16. REFERENCE FILES NEEDED

When building, you will need the alpha-edge-v2.html reference file for the exact CSS and layout.
The report template (alpha_edge_report.html.j2) should be created by converting the reference
HTML into a Jinja2 template — replacing all hardcoded values with template variables while 
keeping the EXACT same CSS, HTML structure, classes, fonts, and Chart.js configuration.

---

## NOW BUILD IT. Start with Phase 1 and work through sequentially. Ask questions only if technically blocked. Ship working code for each phase before moving to the next.
