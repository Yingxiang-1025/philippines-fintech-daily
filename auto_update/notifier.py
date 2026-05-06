"""
WeChat Work (企业微信) webhook notification for Philippines daily news.

Format:
  Part 1 — 昨日动态：200-300字通顺中文重点汇总
  Part 2 — 明细：每条含完整中文提炼 + 原文链接
  Footer — 查看完整日报（可点击直达网站）
Priority: Akulaku > 监管 > Others
"""
import logging
import requests

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    "?key=dd8952d8-8721-40e1-a674-b80d65a229ca"
)

WEBSITE_URL = "https://yingxiang-1025.github.io/ph-fintech-daily/"

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


def _best_section(item: dict) -> str:
    sections = item.get("sections", [])
    if not sections:
        return "other"
    return min(sections, key=lambda s: SECTION_META.get(s, _DEFAULT_META)["priority"])


def _meta(section: str) -> dict:
    return SECTION_META.get(section, _DEFAULT_META)


def _clean(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\n", " ").strip()
    if "<" in out:
        from bs4 import BeautifulSoup
        out = BeautifulSoup(out, "html.parser").get_text()
    return out


def _truncate(text: str, max_len: int = 80) -> str:
    clean = _clean(text)
    if len(clean) <= max_len:
        return clean
    cut = clean[:max_len]
    for sep in ["。", "；", "，", "、", " "]:
        pos = cut.rfind(sep)
        if pos > max_len // 2:
            return cut[:pos + 1].rstrip("，、；") + "…"
    return cut + "…"


def _title_text(item: dict) -> str:
    raw = item.get("title_zh") or item.get("title", "")
    return raw.split("】")[-1].strip() if "】" in raw else raw


def _group_by_section(items: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        sec = _best_section(item)
        groups.setdefault(sec, []).append(item)
    return dict(
        sorted(groups.items(), key=lambda kv: _meta(kv[0])["priority"])
    )


# ─── Part 1: 昨日动态 ────────────────────────────────────

_INNER_CONNECTORS = ["同时，", "此外，", "另外，", "值得关注的是，"]


def _strip_source_suffix(text: str) -> str:
    """Remove trailing source names (e.g. '- Fintech News', '| Reuters')."""
    for sep in [" - ", " — ", " | ", " · "]:
        pos = text.rfind(sep)
        if pos > len(text) // 2:
            text = text[:pos]
    return text.strip()


def _build_digest(groups: dict[str, list[dict]], total: int) -> str:
    """Build 200-300 char fluent, readable Chinese narrative paragraph."""
    all_sentences = []
    items_per_section = max(1, 4 // max(len(groups), 1))

    for sec, items in groups.items():
        prefix = CONNECTORS.get(sec, "此外，")
        for idx, item in enumerate(items[:items_per_section]):
            summary = _clean(item.get("summary_zh") or item.get("summary", ""))
            title = _clean(_title_text(item))
            text = summary if len(summary) > 20 else title
            text = _strip_source_suffix(text)
            text = _truncate(text, 50)

            if idx == 0:
                all_sentences.append(f"{prefix}{text}")
            else:
                conn = _INNER_CONNECTORS[min(idx - 1, len(_INNER_CONNECTORS) - 1)]
                all_sentences.append(f"{conn}{text}")

            if len("。".join(all_sentences) + "。") >= 280:
                break
        if len("。".join(all_sentences) + "。") >= 280:
            break

    digest = "。".join(all_sentences)
    if not digest.endswith("。"):
        digest += "。"
    if len(digest) > 300:
        digest = digest[:297] + "…"
    return digest


# ─── Part 2: 明细 ────────────────────────────────────────

def _build_details(groups: dict[str, list[dict]]) -> list[str]:
    """Build detail lines: each item with full Chinese summary + link."""
    lines = []
    item_no = 0
    for sec, items in groups.items():
        meta = _meta(sec)
        lines.append(f"{meta['emoji']} **{meta['label']}**（{len(items)}条）")
        for item in items[:3]:
            item_no += 1
            title = _truncate(_title_text(item), 50)
            url = item.get("url", "")
            major_tag = "🔴" if item.get("is_major") else ""
            summary = _truncate(
                item.get("summary_zh") or item.get("summary", ""), 80
            )
            if major_tag:
                title = f"{major_tag}{title}"
            lines.append(f"{item_no}. **{title}**")
            if summary:
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
    lines.extend(_build_details(groups))

    lines.append(f"[🌐 查看完整日报]({WEBSITE_URL})")

    return "\n".join(lines)


def send_wechat_notification(new_items: list[dict], today_str: str) -> bool:
    if not new_items:
        logger.info("No new items today — skipping WeChat push.")
        return False

    message = build_message(new_items, today_str)
    if not message:
        return False

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
