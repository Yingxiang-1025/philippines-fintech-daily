"""
Built-in English→Chinese translation for fintech news.
Uses googletrans (primary) with deep-translator as fallback.
"""
import logging
import time

logger = logging.getLogger(__name__)

_gt_translator = None
_deep_translator = None
_active_backend = None


def _init_googletrans():
    global _gt_translator
    if _gt_translator is None:
        try:
            from googletrans import Translator
            _gt_translator = Translator()
            logger.info("googletrans initialized")
        except Exception as e:
            logger.warning(f"googletrans init failed: {e}")
    return _gt_translator


def _init_deep_translator():
    global _deep_translator
    if _deep_translator is None:
        try:
            from deep_translator import GoogleTranslator
            _deep_translator = GoogleTranslator(source="en", target="zh-CN")
            logger.info("deep-translator initialized")
        except Exception as e:
            logger.warning(f"deep-translator init failed: {e}")
    return _deep_translator


def _has_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in (text or ""))


def _translate_googletrans(text: str) -> str | None:
    t = _init_googletrans()
    if not t:
        return None
    try:
        result = t.translate(text[:4500], dest="zh-cn")
        if result and result.text and _has_chinese(result.text):
            return result.text
    except Exception as e:
        logger.debug(f"googletrans failed: {e}")
    return None


def _translate_deep(text: str) -> str | None:
    t = _init_deep_translator()
    if not t:
        return None
    try:
        result = t.translate(text[:4500])
        if result and _has_chinese(result):
            return result
    except Exception as e:
        logger.debug(f"deep-translator failed: {e}")
    return None


def google_translate(text: str, retries: int = 2) -> str:
    """Translate English to Chinese with multi-backend fallback.
    Returns original text unchanged on complete failure."""
    global _active_backend
    if not text or not text.strip():
        return text
    if _has_chinese(text):
        return text

    for attempt in range(retries + 1):
        # Primary: googletrans
        if _active_backend != "deep":
            result = _translate_googletrans(text)
            if result:
                _active_backend = "googletrans"
                return result

        # Fallback: deep-translator
        result = _translate_deep(text)
        if result:
            _active_backend = "deep"
            return result

        if attempt < retries:
            wait = 1.5 * (attempt + 1)
            logger.info(f"Translation retry {attempt+1}, waiting {wait}s...")
            time.sleep(wait)

    logger.warning(f"All translators failed for: {text[:50]}")
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
    "Rappler": "Rappler",
    "CNN Philippines": "CNN菲律宾",
    "ABS-CBN News": "ABS-CBN新闻",
    "Philstar.com": "菲律宾星报",
    "Manila Bulletin": "马尼拉公报",
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
    """Translate summary to Chinese. Strips HTML first."""
    if not summary:
        return summary
    clean = _strip_html(summary)
    return google_translate(clean)


def translate_source(source: str) -> str:
    """Translate source name to Chinese (exact-match dictionary)."""
    return SOURCE_MAP.get(source, source)


def _title_body(title_zh: str) -> str:
    """Extract the body text after the 【xxx】 prefix."""
    if "】" in title_zh:
        return title_zh.split("】", 1)[-1].strip()
    return title_zh


def translate_news_item(item: dict) -> dict:
    """Translate a news item dict in-place. Re-translates if body
    (excluding prefix) still contains no Chinese."""
    summary_en = item.get("summary", "")
    if "<" in summary_en:
        summary_en = _strip_html(summary_en)
        item["summary"] = summary_en

    summary_zh = item.get("summary_zh", "")
    needs_summary = (
        not summary_zh
        or summary_zh == summary_en
        or _looks_garbled(summary_zh)
        or not _has_chinese(summary_zh)
    )
    if needs_summary:
        item["summary_zh"] = translate_summary(summary_en)

    title_zh = item.get("title_zh", "")
    body = _title_body(title_zh)
    if not title_zh or title_zh == item.get("title", "") or not _has_chinese(body):
        item["title_zh"] = translate_title(item.get("title", ""))

    if not item.get("source_zh"):
        item["source_zh"] = translate_source(item.get("source", ""))

    return item


def _looks_garbled(text: str) -> bool:
    """Detect garbled or HTML-contaminated translations."""
    markers = [
        "SEC(证监会)", "BSP(央行)", "人工智能(AI)", "先买后付(BNPL)", "中小微企业(MSME)",
        "<一href", "<一个href", "&nbsp;", 'target="_blank"', "<font color",
    ]
    return any(m in text for m in markers)


def _strip_html(text: str) -> str:
    """Strip HTML tags from text before translation."""
    if "<" in text:
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "html.parser").get_text()
    return text
