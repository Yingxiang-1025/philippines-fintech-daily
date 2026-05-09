"""
WeChat Work (企业微信) webhook notification for Philippines daily news.

Format:
  Part 1 — 昨日动态：200-300字通顺中文段落
  Part 2 — 明细：每条含完整中文标题 + 完整摘要 + 原文链接
  Footer — 查看完整日报链接
Priority: Akulaku > 监管 > Others
"""
import re
import logging
import requests

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    "?key=dd8952d8-8721-40e1-a674-b80d65a229ca"
)

WEBSITE_URL = "https://yingxiang-1025.github.io/philippines-fintech-daily/"

SECTION_META = {
    "akulaku":        {"priority": 0, "label": "Akulaku",  "emoji": "🏦"},
    "regulation":     {"priority": 1, "label": "监管动态", "emoji": "📋"},
    "credit_card":    {"priority": 2, "label": "信用卡",   "emoji": "💳"},
    "digital_lending":{"priority": 3, "label": "数字信贷", "emoji": "💰"},
    "cash_loan":      {"priority": 4, "label": "现金贷",   "emoji": "💵"},
    "bnpl":           {"priority": 5, "label": "BNPL",     "emoji": "🛒"},
    "digital_bank":   {"priority": 6, "label": "数字银行", "emoji": "📱"},
}

_DEFAULT_META = {"priority": 99, "label": "金融科技", "emoji": "📊"}

CONNECTORS = {
    "akulaku": "Akulaku方面，",
    "regulation": "监管层面，",
    "credit_card": "信用卡领域，",
    "digital_lending": "数字信贷方面，",
    "cash_loan": "现金贷方面，",
    "bnpl": "先买后付（BNPL）方面，",
    "digital_bank": "数字银行领域，",
}

_INNER_CONNECTORS = ["同时，", "此外，", "另外，", "值得关注的是，"]


# ─── Text Utils ──────────────────────────────────────────

def _clean(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\n", " ").strip()
    if "<" in out:
        from bs4 import BeautifulSoup
        out = BeautifulSoup(out, "html.parser").get_text()
    return out


def _strip_trailing(text: str) -> str:
    """Strip trailing source names, dangling separators, and URLs."""
    for sep in [" - ", " — ", " | ", " · "]:
        pos = text.rfind(sep)
        if pos > len(text) // 3:
            text = text[:pos].strip()
    text = re.sub(r"\s+[A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)*\s*$", "", text)
    text = re.sub(r"\s*https?://\S+$", "", text)
    return text.strip()


def _sentence_cut(text: str, max_len: int) -> str:
    """Cut text at the last complete sentence boundary within max_len.
    Only cuts at full-stop (。) or semicolon (；) to avoid half-clauses.
    Strips trailing punctuation to prevent double-periods when joined."""
    text = text.rstrip("。；，、 ")
    if len(text) <= max_len:
        return text
    window = text[:max_len]
    for punc in ["。", "；"]:
        pos = window.rfind(punc)
        if pos > max_len * 0.35:
            return window[:pos].rstrip("。；，、 ")
    return window.rstrip("。；，、 ")


def _get_summary(item: dict) -> str:
    raw = _clean(item.get("summary_zh") or item.get("summary", ""))
    return _strip_trailing(raw)


def _title_text(item: dict) -> str:
    raw = item.get("title_zh") or item.get("title", "")
    body = raw.split("】")[-1].strip() if "】" in raw else raw
    return _strip_trailing(body)


# ─── Grouping ────────────────────────────────────────────

def _best_section(item: dict) -> str:
    sections = item.get("sections", [])
    if not sections:
        return "other"
    return min(sections, key=lambda s: SECTION_META.get(s, _DEFAULT_META)["priority"])


def _meta(section: str) -> dict:
    return SECTION_META.get(section, _DEFAULT_META)


def _group_by_section(items: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        sec = _best_section(item)
        groups.setdefault(sec, []).append(item)
    return dict(
        sorted(groups.items(), key=lambda kv: _meta(kv[0])["priority"])
    )


# ─── Part 1: 昨日动态 ────────────────────────────────────

def _build_digest(groups: dict[str, list[dict]], total: int) -> str:
    """Build 200-300 char fluent Chinese paragraph with complete sentences only."""
    all_sentences = []
    items_per_section = max(1, 5 // max(len(groups), 1))

    for sec, items in groups.items():
        prefix = CONNECTORS.get(sec, "此外，")
        for idx, item in enumerate(items[:items_per_section]):
            summary = _get_summary(item)
            title = _title_text(item)
            text = summary if len(summary) > 15 else title
            text = _sentence_cut(text, 90)

            if idx == 0:
                all_sentences.append(f"{prefix}{text}")
            else:
                conn = _INNER_CONNECTORS[min(idx - 1, len(_INNER_CONNECTORS) - 1)]
                all_sentences.append(f"{conn}{text}")

            current = "。".join(all_sentences) + "。"
            if len(current) >= 280:
                break
        if len("。".join(all_sentences) + "。") >= 280:
            break

    digest = "。".join(all_sentences)
    if not digest.endswith("。"):
        digest += "。"
    return digest


# ─── Part 2: 明细 ────────────────────────────────────────

def _build_details(groups: dict[str, list[dict]], digest: str = "") -> list[str]:
    """Build detail lines. Skip summary if already in digest."""
    lines = []
    item_no = 0
    for sec, items in groups.items():
        meta = _meta(sec)
        lines.append(f"{meta['emoji']} **{meta['label']}**（{len(items)}条）")
        for item in items[:3]:
            item_no += 1
            title = _title_text(item)
            url = item.get("url", "")
            major_tag = "🔴" if item.get("is_major") else ""
            summary = _get_summary(item)
            summary = _sentence_cut(summary, 120)

            display_title = f"{major_tag}{title}" if major_tag else title
            lines.append(f"{item_no}. **{display_title}**")
            if summary and summary[:20] not in digest:
                lines.append(f"> {summary}")
            if url:
                lines.append(f"[查看原文]({url})")
        if len(items) > 3:
            lines.append(f"...另有{len(items) - 3}条")
        lines.append("")
    return lines


# ─── Assemble ────────────────────────────────────────────

def build_message(new_items: list[dict], today_str: str) -> str | None:
    if not new_items:
        return None

    groups = _group_by_section(new_items)
    total = len(new_items)
    major_count = sum(1 for n in new_items if n.get("is_major"))
    digest = _build_digest(groups, total)

    lines = [
        f"📰 **菲律宾金融科技日报 | {today_str}**",
        f"新增<font color=\"info\">{total}</font>条资讯",
    ]
    if major_count:
        lines[-1] += f"　其中<font color=\"warning\">{major_count}条重大</font>"
    lines.append("")

    lines.append("**📋 昨日动态**")
    lines.append(f"> {digest}")
    lines.append("")

    lines.append("**📝 明细**")
    lines.extend(_build_details(groups, digest))

    lines.append(f"[🌐 查看完整日报]({WEBSITE_URL})")

    return "\n".join(lines)


def send_wechat_notification(new_items: list[dict], today_str: str) -> bool:
    if not new_items:
        logger.info("No new items today — skipping WeChat push.")
        return False

    items = sorted(new_items, key=lambda n: _meta(_best_section(n))["priority"])
    message = build_message(items, today_str)
    if not message:
        return False

    while len(message.encode("utf-8")) > 3800 and len(items) > 3:
        items = items[:-1]
        message = build_message(items, today_str)
    logger.info(f"Message length: {len(message)} chars, {len(message.encode('utf-8'))} bytes, items: {len(items)}")

    payload = {"msgtype": "markdown", "markdown": {"content": message}}

    try:
        resp = requests.post(WECHAT_WEBHOOK_URL, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info(f"WeChat push OK: {len(new_items)} items sent")
            return True
        logger.warning(f"WeChat webhook error: {result.get('errmsg', '?')}")
        return False
    except Exception as e:
        logger.error(f"WeChat push failed: {e}")
        return False
