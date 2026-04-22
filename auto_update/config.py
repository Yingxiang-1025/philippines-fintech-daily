"""
Configuration for Philippines Fintech Daily Brief auto-updater.
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR
PAGES_DIR = OUTPUT_DIR / "pages"
DATA_DIR = Path(__file__).resolve().parent / "data"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

# ─── OpenAI / LLM API (for Chinese summaries) ───────────
# Set via environment variable or .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
ENABLE_AI_SUMMARY = bool(OPENAI_API_KEY)

# ─── SerpAPI (for Google-like web search) ────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# ─── RSS Feeds ───────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "Fintech News PH",
        "url": "https://fintechnews.ph/feed/",
        "category": "fintech",
    },
    {
        "name": "BusinessWorld",
        "url": "https://www.bworldonline.com/feed/",
        "category": "mainstream",
    },
    {
        "name": "Inquirer Business",
        "url": "https://business.inquirer.net/feed",
        "category": "mainstream",
    },
    {
        "name": "Philippine Star Business",
        "url": "https://www.philstar.com/rss/business",
        "category": "mainstream",
    },
    {
        "name": "Manila Times Business",
        "url": "https://www.manilatimes.net/business/feed/",
        "category": "mainstream",
    },
    {
        "name": "GMA Money",
        "url": "https://www.gmanetwork.com/news/rss/money/feed/",
        "category": "mainstream",
    },
    {
        "name": "BillEase Blog",
        "url": "https://blog.billease.ph/feed/",
        "category": "bnpl",
    },
]

# ─── Web Search Queries (run daily) ─────────────────────
SEARCH_QUERIES = [
    "Philippines fintech lending news today",
    "Philippines credit card digital banking news",
    "Philippines cash loan online lending 2026",
    "Philippines BNPL buy now pay later news",
    "SEC BSP Philippines lending regulation",
    "Akulaku cash loan Philippines",
    "Akulaku Philippines news",
    "GCash Maya Philippines fintech",
    "Philippines digital bank news",
]

# ─── Keyword Filters ────────────────────────────────────
# News must match at least one keyword group to be included

SECTION_KEYWORDS = {
    "regulation": [
        "SEC", "BSP", "Bangko Sentral", "regulation", "moratorium",
        "lending company", "memorandum circular", "compliance",
        "interest rate cap", "consumer protection", "oversight",
        "lending regulation", "OLP", "online lending platform",
    ],
    "credit_card": [
        "credit card", "Mastercard", "Visa", "card loan",
        "card receivable", "card growth", "credit access",
        "Luvit Card", "installment card",
    ],
    "digital_lending": [
        "digital lending", "digital loan", "MSME",
        "SME loan", "business loan", "Fuse Financing",
        "Salmon", "fintech lending", "Maya loan",
        "UnionBank loan", "ADB loan",
    ],
    "cash_loan": [
        "cash loan", "personal loan", "payday loan",
        "microlending", "Grab loan", "Home Credit",
        "instant loan", "quick loan", "emergency loan",
    ],
    "bnpl": [
        "BNPL", "buy now pay later", "BillEase", "Atome",
        "pay later", "installment", "TendoPay",
        "GrabPay Later",
    ],
    "digital_bank": [
        "digital bank", "GoTyme", "Maya Bank", "Tonik",
        "UNOBank", "OFBank", "Union Digital", "GCash",
        "e-wallet", "remittance", "mobile payment",
        "Pera Coach",
    ],
    "akulaku": [
        "Akulaku", "akulaku", "Streetcorner Lending",
    ],
}

# Global relevance filter: an article must contain at least ONE of these
# (kept specific to fintech/finance to avoid noise like mining, politics, etc.)
GLOBAL_KEYWORDS = [
    "fintech", "lending", "loan", "credit card", "digital bank",
    "digital lending", "online lending", "cash loan", "personal loan",
    "BNPL", "buy now pay later", "e-wallet", "mobile payment",
    "GCash", "Maya", "Akulaku", "BillEase", "Atome", "TendoPay",
    "GoTyme", "Tonik", "UNOBank", "Home Credit", "Fuse Financing",
    "Mastercard", "Visa", "interest rate", "remittance",
    "BSP", "Bangko Sentral", "SEC lending", "SEC online",
    "financial inclusion", "financial technology",
    "digital payment", "cryptocurrency", "blockchain",
    "banking-as-a-service", "BaaS", "neobank",
]

# ─── Section → HTML page mapping ────────────────────────
SECTION_PAGES = {
    "regulation": "regulation.html",
    "credit_card": "credit-card.html",
    "digital_lending": "digital-lending.html",
    "cash_loan": "cash-loan.html",
    "bnpl": "bnpl.html",
    "digital_bank": "digital-bank.html",
    "akulaku": "akulaku.html",
}

# ─── Tag styling classes ─────────────────────────────────
SECTION_TAG_CLASSES = {
    "regulation": "tag-regulation",
    "credit_card": "tag-product",
    "digital_lending": "tag-funding",
    "cash_loan": "tag-product",
    "bnpl": "tag-market",
    "digital_bank": "tag-product",
    "akulaku": "tag-akulaku",
}

SECTION_DISPLAY_NAMES = {
    "regulation": "监管",
    "credit_card": "信用卡",
    "digital_lending": "信贷",
    "cash_loan": "现金贷",
    "bnpl": "BNPL",
    "digital_bank": "数字银行",
    "akulaku": "Akulaku",
}
