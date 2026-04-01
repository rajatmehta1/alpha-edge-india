# CLAUDE.md — Alpha Edge Project Context

## What is this project?

Alpha Edge is an **agentic AI pre-market intelligence report generator** for Indian stock market (NSE/BSE) day traders. It runs as a local cron job every trading day at 7:00 AM IST, collects market data from free APIs, computes technical features using Pandas/NumPy, orchestrates 5 AI agents via LangGraph to generate narrative sections, and outputs a beautiful self-contained HTML report.

## Architecture Mantra (NEVER VIOLATE THIS)

**The LLM never generates numbers.** Every price, level, percentage, pattern statistic, and flow figure is computed by deterministic Python code. The LLM (Groq Llama 3.3 70B) ONLY generates narrative text around pre-computed structured data injected via prompt. This prevents hallucination of financial data that could cost traders real money.

## Tech Stack

- **Python 3.11+** — Core runtime
- **LangGraph** — Agent orchestration (parallel fan-out of 5 specialist agents)
- **LangChain + langchain-groq** — LLM abstraction, Groq provider
- **Groq API (free tier)** — Llama 3.3 70B for narrative generation
- **FastAPI** — API layer (future dashboard use)
- **yfinance** — Market data (Nifty, Dow, Brent, USD/INR, Indian stocks)
- **nsetools / nsepython / jugaad-data** — NSE-specific data (options chain, FII/DII, block deals)
- **pandas + numpy + pandas-ta** — Feature engineering, technical indicators
- **scikit-learn** — Pattern matching (KNN cosine similarity on session fingerprints)
- **Jinja2** — HTML report template engine
- **SQLite** — Local storage for historical data + pattern fingerprints
- **Pydantic** — Data models everywhere (strict typing)
- **loguru** — Structured logging
- **tenacity** — Retry logic for flaky API calls
- **rich** — CLI progress output

## Project Structure

```
alpha-edge/
├── CLAUDE.md              # THIS FILE — project context for Claude Code
├── config/                # Settings (Pydantic), constants (stocks, sectors, rules)
├── data/collectors/       # 8 async data collectors:
│   ├── market_data.py     #   SGX Nifty proxy, Dow, Brent, USD/INR, VIX
│   ├── nse_stocks.py      #   Nifty 50 stock OHLCV (yfinance batch)
│   ├── options_chain.py   #   NSE options chain, OI data (nsepython)
│   ├── fii_dii.py         #   FII/DII flows (nsepython + scraper)
│   ├── block_deals.py     #   Block/bulk deals (jugaad-data)
│   ├── news.py            #   RSS feeds with ticker tagging
│   ├── social_sentiment.py #  Stocktwits / simulated sentiment
│   └── tv_analysts.py     #   TV analyst calls (curated + scraper)
├── features/              # 15 feature engineering modules:
│   ├── pipeline.py        #   Master orchestrator (runs all modules in order)
│   ├── technical.py       #   Pivot points, VWAP, ATR, RSI, Fibonacci
│   ├── options_analytics.py #  PCR, max pain, IV rank, unusual OI
│   ├── gap_analysis.py    #   Gap stats, fill rates by regime
│   ├── stock_screener.py  #   Gap-up ranking + entry/target/SL computation
│   ├── sector_rotation.py #   Sector flow scoring
│   ├── correlation.py     #   20-day rolling correlation matrix + anomalies
│   ├── pattern_matching.py #   KNN similarity search on session fingerprints
│   ├── avoid_list.py      #   Stock avoidance rules engine (5 rule types)
│   ├── expiry_analysis.py #   Expiry week stats, OI distribution, theta
│   ├── contagion_chain.py #   Rule-based sector/macro impact chain
│   ├── confidence_score.py #   Weighted ensemble → 0-100 mood score
│   ├── risk_sizing.py     #   Position sizing based on VIX + ATR
│   ├── events_calendar.py #   Weekly events from curated + scraped data
│   ├── watchlist_queue.py #   Time-sequenced intraday alerts
│   └── sentiment.py       #   NLP sentiment scoring per ticker
├── agents/                # 6 LangGraph agents:
│   ├── graph.py           #   StateGraph with fan-out/fan-in topology
│   ├── state.py           #   AgentState TypedDict
│   ├── narrative_agent.py #   Market "why" writer
│   ├── stock_analyst_agent.py # Per-stock catalyst + timing
│   ├── options_agent.py   #   Flow interpretation
│   ├── scenario_agent.py  #   3 if/then playbooks
│   ├── conflict_agent.py  #   TV call vs data contradiction detector
│   ├── watchlist_agent.py #   Time-sequenced alert generator
│   └── prompts/           #   System + user prompts for each agent
├── report/                # Jinja2 renderer + Chart.js data prep + template
│   ├── renderer.py
│   ├── chart_data.py      #   Prepares JSON for all 12 Chart.js charts
│   └── templates/
│       └── alpha_edge_report.html.j2  # Converted from reference HTML
├── storage/               # SQLite database, historical data, pattern store
├── scripts/               # Backfill history, cron setup, manual run
├── reference/             # Reference files
│   └── alpha-edge-v2.html #   Visual reference (DO NOT MODIFY)
├── tests/
├── output/                # Generated reports land here
└── main.py                # Entry point — full pipeline orchestrator
```

## Pipeline Flow

```
07:00 IST  →  Data Ingestion (parallel, 7 collectors, ~3 min)
           →  Feature Engineering (9 compute modules, ~2 min)
           →  Pattern Matching (KNN on SQLite fingerprints, ~30s)
           →  AI Agent Orchestration (5 LangGraph agents via Groq, ~30s)
           →  Report Rendering (Jinja2 + Chart.js, ~10s)
07:06 IST  →  HTML report saved to output/
```

## Key Data Flow

```
Raw API Data (yfinance, NSE, RSS)
    ↓
data/collectors/*.py → data/models.py (RawMarketData)
    ↓
features/pipeline.py → features/models.py (ComputedFeatures)
    ↓                         ↓
    ↓                   agents/graph.py → agents/models.py (AgentNarratives)
    ↓                         ↓
    ↓─────────────────────────↓
                ↓
    report/renderer.py + report/templates/alpha_edge_report.html.j2
                ↓
        output/alpha_edge_YYYY-MM-DD.html
```

## Important Files

| File | Purpose | Notes |
|------|---------|-------|
| `config/settings.py` | All env vars via Pydantic Settings | Reads from `.env` |
| `config/constants.py` | Nifty 50 stocks, sector maps, contagion rules, expiry dates | Static data, update periodically |
| `data/collectors/base.py` | Abstract collector with retry/fallback/provenance | Every collector extends this |
| `features/pipeline.py` | Master orchestrator — calls all 9 feature modules | Outputs `ComputedFeatures` |
| `features/pattern_matching.py` | KNN similarity search on historical sessions | Needs backfilled data to work |
| `agents/graph.py` | LangGraph StateGraph with fan-out/fan-in | Heart of the AI layer |
| `agents/prompts/*.py` | System + user prompts for each agent | Quality of report depends on these |
| `report/templates/alpha_edge_report.html.j2` | The master Jinja2 template | Must match reference design exactly |
| `storage/database.py` | SQLite schema + init | 4 tables: ohlcv, fingerprints, fii_dii, report_log |
| `main.py` | Entry point — runs full pipeline | Called by cron daily |

## Common Commands

```bash
# First-time setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then add GROQ_API_KEY

# Initialize database
python -c "from storage.database import init_db; init_db()"

# Backfill historical data (run once, ~5-10 min)
python scripts/backfill_history.py

# Generate a report manually
python main.py

# Run tests
pytest tests/ -v

# Run a specific collector for debugging
python -c "import asyncio; from data.collectors.market_data import MarketDataCollector; print(asyncio.run(MarketDataCollector().collect()))"
```

## Environment Variables

```
GROQ_API_KEY=gsk_xxx          # Required — get free at console.groq.com
TWITTER_BEARER_TOKEN=          # Optional — social sentiment
REPORT_OUTPUT_DIR=./output     # Where reports are saved
GENERATE_PDF=false             # Set true if weasyprint installed
TRADING_CAPITAL=2400000        # ₹24L — used for risk sizing calculations
LOG_LEVEL=INFO                 # DEBUG for development
```

## Coding Conventions

- **Pydantic models everywhere** — All data structures use Pydantic BaseModel with strict typing. No raw dicts flowing through the system.
- **Async collectors, sync features** — Data collection is async (httpx/aiohttp). Feature computation is sync (Pandas/NumPy). Don't mix.
- **Every number has provenance** — When a collector returns a value, it includes `source`, `timestamp`, and `fresh` boolean. The report can show ⚠ for stale data.
- **Fail gracefully, never crash** — If options chain scraper fails, the report generates without options data. If Groq API fails, the report generates without narrative text. Use `try/except` at every pipeline stage.
- **Structured LLM output** — All agents return Pydantic models, not free-form text. Prompts demand JSON output. Parse with `json.loads()` + Pydantic validation.
- **No LLM-generated numbers** — Repeat: the LLM writes prose, not data. If you see a number in a prompt's output, it MUST have come from the `ComputedFeatures` input, not model generation.

## Groq Free Tier Limits

- 30 requests/minute, ~6,000 tokens/minute
- Strategy: Run 5 agents sequentially with 2-second delays (not parallel) to stay within limits
- Total LLM time: ~30 seconds for all 5 agents
- If rate limited, retry with exponential backoff (tenacity handles this)

## NSE Data Scraping Notes

- NSE website blocks automated requests aggressively
- Always set browser-like User-Agent headers
- Add 1-2 second delays between NSE requests
- nsepython can break when NSE changes their API — always have yfinance fallback
- Options chain data is the most fragile source — handle `None`/empty gracefully

## Report Template Notes

- The Jinja2 template (`alpha_edge_report.html.j2`) is a conversion of the reference HTML file `alpha-edge-v2.html`
- All hardcoded values become `{{ template_variables }}`
- CSS is kept inline in the template (same phosphor terminal theme)
- Chart.js data is injected as inline `<script>` JSON
- The output is a single self-contained HTML file (no external deps except Google Fonts + Chart.js CDN)
- Use `{{ variable | tojson }}` for Chart.js data arrays
- Use `{{ variable | safe }}` for HTML content from AI agents (sanitize first!)

## Pattern Matching System

The "18 similar events, 72% win rate" feature works like this:
1. Every historical trading session gets encoded as a 15-dimension feature vector (gap_pct, crude_change, vix, pcr, sector, day_of_week, etc.)
2. Vectors stored in SQLite `session_fingerprints` table
3. Today's setup gets the same encoding (minus outcome)
4. scikit-learn `NearestNeighbors` (cosine similarity) finds top-20 matches
5. Outcome statistics computed from matched sessions
6. Needs `scripts/backfill_history.py` to run first (populates 2+ years of data)

## Testing

- `tests/fixtures/` contains sample API responses for mocking
- Test collectors with mocked HTTP responses (don't hit real APIs in tests)
- Test features with known input/output pairs
- Test agents with sample `ComputedFeatures` fixture
- Test renderer with sample data to verify HTML generation

## Upgrade Path (Future)

| Current | Future | Trigger |
|---------|--------|---------|
| Groq Llama 3.3 | Claude Sonnet API | When narrative quality needs to be best-in-class |
| yfinance | Kite Connect (Zerodha) | When you need real-time + reliable NSE data |
| SQLite | TimescaleDB + Qdrant | When pattern DB exceeds 1M rows |
| Local cron | Railway / Modal.com | When you want cloud execution |
| None | Resend + Telegram bot | When you want automated delivery |
| Rule-based contagion | Neo4j graph DB | When you want dynamic contagion chain traversal |

## Feature Module Dependency Chain

The feature pipeline must execute in this order (some modules depend on others):

1. `technical.py` — needs: OHLCV data
2. `options_analytics.py` — needs: options chain data
3. `gap_analysis.py` — needs: technical levels, macro data
4. `sector_rotation.py` — needs: stock data, FII/DII flows
5. `stock_screener.py` — needs: gap_analysis, options_analytics, sector_rotation
6. `correlation.py` — needs: macro data, historical prices
7. `pattern_matching.py` — needs: stock_screener output, historical fingerprints
8. `avoid_list.py` — needs: stock data, options, block deals, news
9. `expiry_analysis.py` — needs: options_analytics, gap_analysis
10. `contagion_chain.py` — needs: macro data catalyst detection
11. `confidence_score.py` — needs: ALL of the above
12. `risk_sizing.py` — needs: confidence_score, VIX, ATR
13. `events_calendar.py` — needs: date, earnings calendar
14. `watchlist_queue.py` — needs: stock_screener, nifty levels, expiry
15. `sentiment.py` — needs: social data, news data

## Report Sections → Data Source Mapping

| Section | Primary Data Source | Needs AI Agent? |
|---------|-------------------|-----------------|
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

AI agents write text for 6 of 17 sections. The other 11 are pure data templates.
If Groq API fails, those 11 sections still render perfectly.
