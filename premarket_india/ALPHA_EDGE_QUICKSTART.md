# ALPHA EDGE — Quick Start for Claude Code

## HOW TO USE THIS IN CLAUDE CODE

### Step 1: Start a new Claude Code session
Open Claude Code (terminal) and navigate to where you want the project:
```bash
cd ~/projects
mkdir alpha-edge && cd alpha-edge
```

### Step 2: Drop the prompt
You need FIVE files ready before starting:
1. **`CLAUDE.md`** — Project context file (Claude Code reads this automatically)
2. **`ALPHA_EDGE_CLAUDE_CODE_PROMPT.md`** — The full build spec (main prompt)
3. **`ALPHA_EDGE_PROMPT_PATCH.md`** — Fixes 12 structural gaps (missing modules, sections, charts)
4. **`ALPHA_EDGE_FINAL_REVIEW.md`** — Fixes 20 accuracy issues (financial formulas, AI reliability, UX)
5. **`alpha-edge-v2.html`** — The visual reference report (from our earlier conversation)

**First message to Claude Code:**
```
Create a new project called alpha-edge. Here is the CLAUDE.md file for the project:

[paste entire CLAUDE.md contents here]

Save this as CLAUDE.md in the project root. Confirm when done.
```

**Second message:**
```
Now here is the full engineering spec. Read it COMPLETELY before building anything.

[paste ENTIRE ALPHA_EDGE_CLAUDE_CODE_PROMPT.md]

DO NOT start building yet — I have critical patches to apply first.
```

**Third message:**
```
IMPORTANT: Here are critical fixes to the spec above. Read and merge these 
into your understanding before building anything.

PATCH 1 — Structural gaps (12 fixes):
[paste ENTIRE ALPHA_EDGE_PROMPT_PATCH.md]

PATCH 2 — Accuracy and reliability fixes (20 fixes from senior review):
[paste ENTIRE ALPHA_EDGE_FINAL_REVIEW.md]

Now acknowledge all changes. You should now have:
- 8 data collectors (not 7)
- 15 feature modules (not 9)  
- 6 LangGraph agents (not 5)
- agents/json_utils.py for robust Groq JSON parsing
- Corrected max pain formula, VWAP proxy, HV Rank proxy, simplified options skew
- Sector-filtered pattern matching (not raw cosine on mixed types)
- Auto-backfill on first run
- Dynamic footer metadata
- Conditional expiry section rendering
- Complete variable mapping for all 17 report sections
- Exact Chart.js specs for all 12 canvases

Confirm your understanding, then create the directory structure, pyproject.toml, 
requirements.txt, .env.example, config files, and ALL Pydantic models.
```

**Fourth message:**
```
Here is the reference report HTML. The final output MUST match this EXACTLY.
Copy the CSS verbatim. Keep all class names. Only replace hardcoded values 
with Jinja2 template variables.

[paste entire alpha-edge-v2.html]

Save this as reference/alpha-edge-v2.html in the project. 
Now implement all 8 data collectors per the spec.
```

**Fifth message:**
```
Now implement all 15 feature engineering modules. Follow the dependency chain 
from CLAUDE.md — some modules depend on others. Start with technical.py, 
then options_analytics.py, then stock_screener.py, and so on.
```

**Sixth message:**
```
Now implement the LangGraph agent graph with all 6 agents and their prompts.
Make sure the graph uses fan-out (parallel or sequential with delays for 
Groq rate limits). Each agent returns a Pydantic model, not free text.
```

**Seventh message:**
```
Now convert alpha-edge-v2.html into the Jinja2 template. Copy CSS verbatim. 
Replace ALL hardcoded values with template variables per the mapping in the 
patch document. Implement chart_data.py with all 12 Chart.js configurations.
Implement renderer.py to merge ComputedFeatures + AgentNarratives into the template.
```

**Eighth message:**
```
Now wire up main.py, SQLite database, backfill script, and test the full 
pipeline end-to-end. The report should open in the browser automatically 
after generation. Fix any issues until `python main.py` produces a report 
that matches alpha-edge-v2.html visually.
```

### Step 4: Set up environment
After Claude Code creates the project, run:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up env vars
cp .env.example .env
# Edit .env and add your Groq API key (get free at https://console.groq.com)

# Initialize database
python -c "from storage.database import init_db; init_db()"

# Backfill historical data (run once, takes 5-10 minutes)
python scripts/backfill_history.py

# Generate your first report!
python main.py
```

### Step 5: Set up daily cron (Mac)
```bash
# Open crontab editor
crontab -e

# Add this line (adjust path to your project):
0 7 * * 1-5 cd ~/projects/alpha-edge && ~/projects/alpha-edge/venv/bin/python main.py >> ~/projects/alpha-edge/output/cron.log 2>&1
```

---

## GETTING YOUR FREE API KEYS

### Groq (Required — Free)
1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. Go to API Keys → Create API Key
4. Copy the key starting with `gsk_...`
5. Add to `.env` as `GROQ_API_KEY=gsk_xxxxxxx`

Free tier limits:
- 30 requests/minute
- ~6,000 tokens/minute
- 14,400 requests/day
- More than enough for 5 agent calls per report

### Twitter/X API (Optional — Free-ish)
1. Go to https://developer.twitter.com
2. Sign up for Basic tier ($100/mo) OR skip this entirely
3. The system works fine without Twitter — it will use Stocktwits (free, no auth)
   or simulated sentiment data

### Everything else is FREE:
- yfinance: No API key needed
- nsetools: No API key needed  
- nsepython: No API key needed
- jugaad-data: No API key needed
- RSS feeds: No API key needed
- Stocktwits: No API key needed
- SQLite: Local, free

---

## EXPECTED COSTS

| Component | Monthly Cost |
|-----------|-------------|
| Groq API | $0 (free tier) |
| yfinance | $0 (free) |
| NSE data | $0 (free scraping) |
| SQLite | $0 (local) |
| Hosting | $0 (local cron) |
| **TOTAL** | **$0 / month** |

---

## UPGRADE PATH (When you're ready)

| Current (Free) | Upgrade To | When | Cost |
|----------------|-----------|------|------|
| Groq Llama 3.3 | Claude Sonnet API | When quality matters | ~$17/yr |
| yfinance | Kite Connect (Zerodha) | When you need real-time data | ₹2,000/mo |
| SQLite | TimescaleDB + Qdrant | When pattern DB > 1M rows | ~$30/mo |
| Local cron | Railway / Modal | When you want it in the cloud | ~$12/mo |
| None | Resend + Telegram Bot | When you want delivery | ~$0-5/mo |

---

## TROUBLESHOOTING

### "nsepython is failing / NSE blocking requests"
NSE changes their API frequently. Try:
```python
# In options_chain.py, add these headers:
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}
# Also add 2-second delays between NSE requests
```
If it still fails, the system falls back to yfinance for stock data (which always works).

### "Groq rate limit hit"
Change agents/graph.py to run agents sequentially instead of parallel:
```python
# Instead of asyncio.gather(), run one at a time with 3-second delays:
narrative = await narrative_agent(state)
await asyncio.sleep(3)
stock_analysis = await stock_analyst_agent(state)
await asyncio.sleep(3)
# ... etc
```

### "yfinance returning empty data for Indian stocks"
Some Indian stocks need the `.NS` suffix. Check YFINANCE_TICKER_MAP in constants.py.
Also, yfinance data is delayed by ~15 minutes. For pre-market work, this is fine since
we're looking at previous day's data anyway.

### "Report looks different from the reference"
The most common issue is Jinja2 template escaping HTML entities. Use:
```jinja2
{{ variable | safe }}  {# For HTML content #}
{{ variable }}         {# For plain text/numbers #}
```

### "Pattern matching returns no results"
You need to run `scripts/backfill_history.py` first to populate the historical database.
The pattern engine needs at least 200+ trading sessions of data to be useful.
