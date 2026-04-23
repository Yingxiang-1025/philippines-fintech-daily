"""
Built-in English→Chinese translation for fintech news.
Uses Google Translate (free, via deep-translator) for full-sentence translation.
Falls back to clean English if translation unavailable.
"""
import logging
import time

logger = logging.getLogger(__name__)

_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source="en", target="zh-CN")
            logger.info("Google Translator initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to init Google Translator: {e}")
    return _translator


def google_translate(text: str) -> str:
    """Translate English text to Chinese via free Google Translate.
    Returns original text unchanged on any failure."""
    if not text or not text.strip():
        return text
    translator = _get_translator()
    if not translator:
        return text
    try:
        chunk = text[:4500] if len(text) > 4500 else text
        result = translator.translate(chunk)
        time.sleep(0.35)
        return result if result else text
    except Exception as e:
        logger.warning(f"Google Translate failed: {e}")
        return text


SOURCE_MAP = {
    "Fintech News PH": "菲律宾金融科技新闻",
    "BusinessWorld": "商业世界",
    "Inquirer Business": "询问者商业版",
    "Philippine Star Business": "菲律宾星报商业版",
    "Manila Times Business": "马尼拉时报商业版",
    "GMA Money": "GMA财经",
    "BillEase Blog": "BillEase博客",
    "Google News": "谷歌新闻",
    "Yahoo Finance": "雅虎财经",
}


def _title_prefix(title: str) -> str:
    """Determine a Chinese category prefix based on English title keywords."""
    t = title.lower()
    if "akulaku" in t:
        return "【Akulaku】"
    if any(k in t for k in ["sec ", "bsp ", "regulation", "moratorium", "oversight", "compliance"]):
        return "【监管】"
    if any(k in t for k in ["credit card", "mastercard", "visa "]):
        return "【信用卡】"
    if any(k in t for k in ["bnpl", "buy now pay later", "billease", "atome", "paylater"]):
        return "【BNPL】"
    if any(k in t for k in ["cash loan", "payday", "microlend"]):
        return "【现金贷】"
    if any(k in t for k in ["digital bank", "gotyme", "maya bank", "tonik", "gcash", "e-wallet"]):
        return "【数字银行】"
    if any(k in t for k in ["lending", "loan", "credit", "msme", "financing"]):
        return "【信贷】"
    if any(k in t for k in ["raises", "funding", "investment", " million", " billion"]):
        return "【融资】"
    if any(k in t for k in ["fintech", "digital", "payment", "remittance"]):
        return "【金融科技】"
    return "【金融科技】"


def translate_title(title: str) -> str:
    """Translate title to Chinese with a category prefix."""
    prefix = _title_prefix(title)
    zh = google_translate(title)
    return f"{prefix} {zh}"


def translate_summary(summary: str) -> str:
    """Translate summary to Chinese using Google Translate. Strips HTML first."""
    if not summary:
        return summary
    clean = _strip_html(summary)
    return google_translate(clean)


def translate_source(source: str) -> str:
    """Translate source name to Chinese (exact-match dictionary)."""
    return SOURCE_MAP.get(source, source)


def translate_news_item(item: dict) -> dict:
    """Translate a news item dict in-place. Skips items that already have
    good translations to avoid unnecessary API calls and rate limits."""
    summary_en = item.get("summary", "")
    if "<" in summary_en:
        summary_en = _strip_html(summary_en)
        item["summary"] = summary_en

    summary_zh = item.get("summary_zh", "")
    needs_summary = (
        not summary_zh
        or summary_zh == summary_en
        or _looks_garbled(summary_zh)
    )
    if needs_summary:
        item["summary_zh"] = translate_summary(summary_en)

    title_zh = item.get("title_zh", "")
    if not title_zh or title_zh == item.get("title", ""):
        item["title_zh"] = translate_title(item.get("title", ""))

    if not item.get("source_zh"):
        item["source_zh"] = translate_source(item.get("source", ""))

    return item


def _looks_garbled(text: str) -> bool:
    """Detect garbled or HTML-contaminated translations."""
    markers = [
        "SEC(证监会)", "BSP(央行)", "人工智能(AI)", "先买后付(BNPL)", "中小微企业(MSME)",
        "<一href", "<一个href", "&nbsp;", "target=\"_blank\"", "<font color",
    ]
    return any(m in text for m in markers)


def _strip_html(text: str) -> str:
    """Strip HTML tags from text before translation."""
    if "<" in text:
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "html.parser").get_text()
    return text
