"""Alpha Edge — Trading constants, sector mappings, contagion rules, expiry dates."""

# ── Nifty 50 stocks with sector mapping and approximate index weight ──
NIFTY_50_STOCKS = {
    "RELIANCE": {"name": "Reliance Industries", "sector": "Oil & Gas", "weight": 10.2},
    "TCS": {"name": "Tata Consultancy Services", "sector": "IT", "weight": 4.1},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Banking", "weight": 8.8},
    "INFY": {"name": "Infosys", "sector": "IT", "weight": 5.6},
    "ICICIBANK": {"name": "ICICI Bank", "sector": "Banking", "weight": 6.2},
    "HINDUNILVR": {"name": "Hindustan Unilever", "sector": "FMCG", "weight": 3.0},
    "ITC": {"name": "ITC Ltd", "sector": "FMCG", "weight": 3.8},
    "SBIN": {"name": "State Bank of India", "sector": "Banking", "weight": 2.8},
    "BHARTIARTL": {"name": "Bharti Airtel", "sector": "Telecom", "weight": 3.5},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank", "sector": "Banking", "weight": 2.5},
    "LT": {"name": "Larsen & Toubro", "sector": "Infra", "weight": 3.2},
    "AXISBANK": {"name": "Axis Bank", "sector": "Banking", "weight": 2.3},
    "ASIANPAINT": {"name": "Asian Paints", "sector": "Paints", "weight": 1.2},
    "MARUTI": {"name": "Maruti Suzuki", "sector": "Auto", "weight": 1.8},
    "BAJFINANCE": {"name": "Bajaj Finance", "sector": "NBFC", "weight": 2.1},
    "TITAN": {"name": "Titan Company", "sector": "Consumer", "weight": 1.5},
    "SUNPHARMA": {"name": "Sun Pharma", "sector": "Pharma", "weight": 2.0},
    "TATAMOTORS": {"name": "Tata Motors", "sector": "Auto", "weight": 2.1},
    "WIPRO": {"name": "Wipro", "sector": "IT", "weight": 1.0},
    "HCLTECH": {"name": "HCL Technologies", "sector": "IT", "weight": 2.8},
    "ULTRACEMCO": {"name": "UltraTech Cement", "sector": "Cement", "weight": 1.2},
    "NTPC": {"name": "NTPC", "sector": "Power", "weight": 1.5},
    "POWERGRID": {"name": "Power Grid Corp", "sector": "Power", "weight": 1.1},
    "TATASTEEL": {"name": "Tata Steel", "sector": "Metals", "weight": 1.0},
    "ONGC": {"name": "ONGC", "sector": "Oil & Gas", "weight": 1.0},
    "NESTLEIND": {"name": "Nestle India", "sector": "FMCG", "weight": 0.8},
    "M&M": {"name": "Mahindra & Mahindra", "sector": "Auto", "weight": 2.5},
    "JSWSTEEL": {"name": "JSW Steel", "sector": "Metals", "weight": 0.9},
    "ADANIENT": {"name": "Adani Enterprises", "sector": "Conglomerate", "weight": 1.0},
    "ADANIPORTS": {"name": "Adani Ports", "sector": "Infra", "weight": 1.2},
    "TECHM": {"name": "Tech Mahindra", "sector": "IT", "weight": 1.0},
    "BAJAJFINSV": {"name": "Bajaj Finserv", "sector": "NBFC", "weight": 0.9},
    "COALINDIA": {"name": "Coal India", "sector": "Metals", "weight": 0.8},
    "INDUSINDBK": {"name": "IndusInd Bank", "sector": "Banking", "weight": 1.1},
    "GRASIM": {"name": "Grasim Industries", "sector": "Cement", "weight": 0.9},
    "CIPLA": {"name": "Cipla", "sector": "Pharma", "weight": 0.8},
    "DRREDDY": {"name": "Dr. Reddy's", "sector": "Pharma", "weight": 0.7},
    "APOLLOHOSP": {"name": "Apollo Hospitals", "sector": "Pharma", "weight": 0.7},
    "EICHERMOT": {"name": "Eicher Motors", "sector": "Auto", "weight": 0.7},
    "DIVISLAB": {"name": "Divi's Laboratories", "sector": "Pharma", "weight": 0.6},
    "BPCL": {"name": "Bharat Petroleum", "sector": "Oil & Gas", "weight": 0.5},
    "HEROMOTOCO": {"name": "Hero MotoCorp", "sector": "Auto", "weight": 0.6},
    "TRENT": {"name": "Trent Ltd", "sector": "Retail", "weight": 0.9},
    "INDIGO": {"name": "InterGlobe Aviation", "sector": "Aviation", "weight": 0.8},
    "HINDALCO": {"name": "Hindalco", "sector": "Metals", "weight": 0.8},
    "BRITANNIA": {"name": "Britannia Industries", "sector": "FMCG", "weight": 0.5},
    "SBILIFE": {"name": "SBI Life Insurance", "sector": "Insurance", "weight": 0.5},
    "HDFCLIFE": {"name": "HDFC Life Insurance", "sector": "Insurance", "weight": 0.5},
    "SHRIRAMFIN": {"name": "Shriram Finance", "sector": "NBFC", "weight": 0.5},
    "TATACONSUM": {"name": "Tata Consumer", "sector": "FMCG", "weight": 0.5},
}

SECTORS = [
    "Banking", "IT", "Oil & Gas", "Auto", "Pharma", "FMCG",
    "Metals", "Paints", "Aviation", "Retail", "Telecom", "Infra",
    "Power", "Cement", "NBFC", "Consumer", "Insurance", "Conglomerate",
]

# ── yfinance ticker mappings ──
YFINANCE_TICKER_MAP = {
    **{ticker: f"{ticker}.NS" for ticker in NIFTY_50_STOCKS},
    # Fix tickers that differ from NSE symbol
    "M&M": "M&M.NS",
    # Macro tickers
    "SGX_NIFTY": "^NSEI",
    "DOW_FUTURES": "YM=F",
    "BRENT_CRUDE": "BZ=F",
    "USDINR": "USDINR=X",
    "INDIA_VIX": "^INDIAVIX",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}

# ── Sector sensitivity to crude/forex ──
# Positive = benefits from factor increase, Negative = hurt
# These are heuristic estimates. TODO: replace with regression-fitted values after backfill.
SECTOR_SENSITIVITY = {
    "Aviation": {"crude": -1.8, "usdinr": -0.3},
    "Paints": {"crude": -1.2, "usdinr": -0.2},
    "Auto": {"crude": -0.8, "usdinr": -0.3},
    "FMCG": {"crude": -0.4, "usdinr": -0.1},
    "Oil & Gas": {"crude": 1.0, "usdinr": 0.2},
    "Metals": {"crude": 0.3, "usdinr": 0.5},
    "IT": {"crude": 0.0, "usdinr": -1.2},
    "Banking": {"crude": -0.2, "usdinr": -0.3},
    "Pharma": {"crude": -0.2, "usdinr": -0.8},
    "Telecom": {"crude": -0.1, "usdinr": -0.1},
    "Infra": {"crude": -0.3, "usdinr": -0.1},
    "Power": {"crude": -0.5, "usdinr": 0.0},
    "Cement": {"crude": -0.3, "usdinr": -0.1},
    "NBFC": {"crude": -0.1, "usdinr": -0.2},
    "Retail": {"crude": -0.3, "usdinr": -0.1},
    "Consumer": {"crude": -0.2, "usdinr": -0.1},
    "Insurance": {"crude": -0.1, "usdinr": -0.1},
    "Conglomerate": {"crude": 0.0, "usdinr": 0.0},
}

# ── Contagion chain rules ──
CONTAGION_RULES = {
    "crude_down": {
        "1st_order": {
            "beneficiaries": [
                {"name": "Airlines (IndiGo, SpiceJet)", "emoji": "✈", "desc": "ATF = 40% of opex → direct margin expansion"},
                {"name": "Paints (Asian, Berger)", "emoji": "🎨", "desc": "Crude derivatives = 35% of raw material cost"},
                {"name": "Tyres (MRF, Apollo)", "emoji": "🛞", "desc": "Synthetic rubber feedstock linked to crude"},
            ],
            "losers": [
                {"name": "OMCs (IOC, BPCL, HPCL)", "emoji": "⛽", "desc": "Inventory markdown losses on stored crude"},
            ],
        },
        "2nd_order": {
            "beneficiaries": [
                {"name": "Logistics (Delhivery, TCI)", "emoji": "🚚", "desc": "Lower diesel costs → margin improvement"},
                {"name": "FMCG (HUL, Dabur)", "emoji": "🧴", "desc": "Packaging costs decline, input cost relief"},
            ],
            "neutral": [
                {"name": "Petchem (RIL segment)", "emoji": "🏗", "desc": "Lower feedstock but lower realization — net neutral"},
            ],
            "losers": [
                {"name": "Upstream (ONGC, Oil India)", "emoji": "🔧", "desc": "Lower crude realization → revenue pressure"},
            ],
        },
        "3rd_order": {
            "beneficiaries": [
                {"name": "RBI Rate Cut Prob ↑", "emoji": "📉", "desc": "Lower crude → lower CPI → more cuts"},
                {"name": "Current Account ↑", "emoji": "💵", "desc": "$1/bbl decline saves India ~$2.1B annually"},
                {"name": "FII EM Flows ↑", "emoji": "🌏", "desc": "Lower oil + Fed cut odds → positive EM signal"},
            ],
            "neutral": [
                {"name": "Fiscal Deficit", "emoji": "💰", "desc": "Subsidy down but excise revenue down — mild net positive"},
            ],
        },
    },
    "crude_up": {
        "1st_order": {
            "beneficiaries": [
                {"name": "OMCs (IOC, BPCL, HPCL)", "emoji": "⛽", "desc": "Inventory gains on stored crude"},
                {"name": "Upstream (ONGC, Oil India)", "emoji": "🔧", "desc": "Higher crude realization → revenue boost"},
            ],
            "losers": [
                {"name": "Airlines (IndiGo, SpiceJet)", "emoji": "✈", "desc": "ATF cost surge → margin compression"},
                {"name": "Paints (Asian, Berger)", "emoji": "🎨", "desc": "Raw material cost inflation"},
                {"name": "Tyres (MRF, Apollo)", "emoji": "🛞", "desc": "Input cost pressure"},
            ],
        },
        "2nd_order": {
            "beneficiaries": [],
            "losers": [
                {"name": "Logistics (Delhivery, TCI)", "emoji": "🚚", "desc": "Diesel costs surge → margin hit"},
                {"name": "FMCG (HUL, Dabur)", "emoji": "🧴", "desc": "Packaging & transport cost inflation"},
            ],
            "neutral": [
                {"name": "Petchem (RIL segment)", "emoji": "🏗", "desc": "Higher feedstock but higher realization — net neutral"},
            ],
        },
        "3rd_order": {
            "beneficiaries": [],
            "losers": [
                {"name": "RBI Rate Cut Prob ↓", "emoji": "📉", "desc": "Higher crude → higher CPI → delayed cuts"},
                {"name": "Current Account ↓", "emoji": "💵", "desc": "Oil import bill increases"},
                {"name": "FII EM Flows ↓", "emoji": "🌏", "desc": "Higher oil = EM risk-off signal"},
            ],
            "neutral": [
                {"name": "Fiscal Deficit", "emoji": "💰", "desc": "More subsidy burden but higher excise — mixed"},
            ],
        },
    },
    "fed_dovish": {
        "1st_order": {
            "beneficiaries": [
                {"name": "IT (TCS, Infy, Wipro)", "emoji": "💻", "desc": "Client spending improves with lower rates"},
                {"name": "FII Flows ↑", "emoji": "🌏", "desc": "Dollar weakens → EM allocation increases"},
            ],
            "losers": [],
        },
        "2nd_order": {
            "beneficiaries": [
                {"name": "Banking (rate-sensitive)", "emoji": "🏦", "desc": "RBI follows Fed → NIMs may compress but loan growth rises"},
                {"name": "Real Estate", "emoji": "🏠", "desc": "Lower rates → housing demand boost"},
            ],
            "losers": [],
            "neutral": [],
        },
        "3rd_order": {
            "beneficiaries": [
                {"name": "INR Strengthens", "emoji": "💵", "desc": "Weaker USD → INR appreciation"},
            ],
            "losers": [
                {"name": "IT (translation loss)", "emoji": "💻", "desc": "INR strength = lower translated earnings"},
            ],
            "neutral": [],
        },
    },
    "inr_weaken": {
        "1st_order": {
            "beneficiaries": [
                {"name": "IT (TCS, Infy)", "emoji": "💻", "desc": "Higher translated earnings in INR"},
                {"name": "Pharma (exporters)", "emoji": "💊", "desc": "Export revenue boost"},
            ],
            "losers": [
                {"name": "Oil importers", "emoji": "⛽", "desc": "Higher import bill in INR terms"},
            ],
        },
        "2nd_order": {
            "beneficiaries": [],
            "losers": [
                {"name": "FMCG (imported inputs)", "emoji": "🧴", "desc": "Input cost inflation from imports"},
            ],
            "neutral": [],
        },
        "3rd_order": {
            "beneficiaries": [],
            "losers": [
                {"name": "FII Confidence ↓", "emoji": "🌏", "desc": "Currency depreciation → EM risk-off"},
            ],
            "neutral": [],
        },
    },
}

# ── Expiry calendar 2026 (monthly — last Thursday of each month) ──
EXPIRY_DATES_2026 = [
    "2026-01-29", "2026-02-26", "2026-03-26", "2026-04-30",
    "2026-05-28", "2026-06-25", "2026-07-30", "2026-08-27",
    "2026-09-24", "2026-10-29", "2026-11-26", "2026-12-31",
]

# ── TV Analyst database ──
TV_ANALYSTS = {
    "Sudarshan Sukhani": {"channel": "CNBC-TV18", "accuracy_30d": 0.61},
    "Prakash Gaba": {"channel": "CNBC Awaaz", "accuracy_30d": 0.54},
    "Kunal Bothra": {"channel": "CNBC-TV18", "accuracy_30d": 0.58},
    "Rajat Bose": {"channel": "ET Now", "accuracy_30d": 0.48},
}

# ── News ticker keyword mapping ──
TICKER_KEYWORDS = {
    "INDIGO": ["indigo", "interglobe", "aviation", "airline", "atf"],
    "RELIANCE": ["reliance", "ril", "jio", "reliance industries"],
    "TCS": ["tcs", "tata consultancy"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ASIANPAINT": ["asian paints", "asianpaint", "asian paint"],
    "INFY": ["infosys", "infy"],
    "ICICIBANK": ["icici bank", "icicibank"],
    "TATAMOTORS": ["tata motors", "tatamotors"],
    "SBIN": ["sbi", "state bank"],
    "TRENT": ["trent", "zudio", "westside"],
    "BPCL": ["bpcl", "bharat petroleum"],
    "ONGC": ["ongc"],
    "MARUTI": ["maruti", "maruti suzuki"],
    "WIPRO": ["wipro"],
    "HCLTECH": ["hcl tech", "hcltech"],
    "BHARTIARTL": ["airtel", "bharti airtel"],
    "TITAN": ["titan"],
    "SUNPHARMA": ["sun pharma", "sunpharma"],
    "LT": ["l&t", "larsen"],
    "KOTAKBANK": ["kotak", "kotak bank"],
    # Macro keywords
    "CRUDE": ["crude", "brent", "opec", "oil price", "petroleum"],
    "RBI": ["rbi", "monetary policy", "rate cut", "repo rate"],
    "FED": ["fed", "federal reserve", "fomc", "powell"],
    "FII": ["fii", "foreign institutional"],
    "DII": ["dii", "domestic institutional"],
}

# ── Nifty lot size ──
NIFTY_LOT_SIZE = 25
BANKNIFTY_LOT_SIZE = 15

# ── RSS feed URLs ──
RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/latestnews.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
]

# ── Confidence score weights ──
CONFIDENCE_WEIGHTS = {
    "sgx_direction": 0.15,
    "vix_direction": 0.12,
    "pcr_signal": 0.10,
    "fii_flow": 0.10,
    "dii_flow": 0.08,
    "crude_for_india": 0.10,
    "dow_direction": 0.08,
    "sector_breadth": 0.08,
    "news_sentiment": 0.06,
    "social_sentiment": 0.05,
    "expiry_adj": 0.05,
    "rsi_signal": 0.03,
}

# ── Expected open regression coefficients ──
# TODO: Replace with regression-fitted values after backfill script runs.
# These are heuristic estimates based on observed Nifty-global correlations.
EXPECTED_OPEN_COEFFICIENTS = {
    "dow_weight": 0.4,
    "brent_weight": -0.15,
    "usdinr_weight": -0.10,
}

# ── Stock screener weights ──
SCREENER_WEIGHTS = {
    "gap_score": 0.25,
    "catalyst_score": 0.20,
    "flow_score": 0.15,
    "pattern_score": 0.15,
    "volume_score": 0.10,
    "avoid_penalty": -0.50,
    "rsi_penalty": -0.15,
}
