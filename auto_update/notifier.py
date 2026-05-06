"""
WeChat Work (企业微信) webhook notification for daily news updates.

Design informed by internal-comms best practices:
  - Newsletter pattern: emoji section headers + concise bullets
  - 3P principle: data-driven, scannable in 30-60s
  - General comms: important-first, active voice, include links
  - Priority: Akulaku > Regulation > Others
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
    return clean[:max_len] + "…" if len(clean) > max_len else clean


def _title_text(item: dict) -> str:
    raw = item.get("title_zh") or item.get("title", "")
    return raw.split("】")[-1].strip() if "】" in raw else raw


def _group_by_section(items: list[dict]) -> dict[str, list[dict]]:
    """Group items by their best section, preserving priority order."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        sec = _best_section(item)
        groups.setdefault(sec, []).append(item)
    return dict(
        sorted(groups.items(), key=lambda kv: _meta(kv[0])["priority"])
    )


def _build_digest(groups: dict[str, list[dict]], total: int) -> str:
    """Build a narrative digest (100-200 chars) highlighting each sector's key move."""
    parts = []
    for sec, items in groups.items():
        meta = _meta(sec)
        top = items[0]
        summary = _clean(top.get("summary_zh") or top.get("summary", ""))
        title = _title_text(top)
        brief = _truncate(summary, 45) if summary else _truncate(title, 35)
        parts.append(f"{meta['label']}：{brief}")
        if len("；".join(parts)) >= 170:
            break

    digest = "；".join(parts)
    if len(digest) > 200:
        digest = digest[:197] + "…"
    if not digest.endswith("。"):
        digest += "。"
    return digest


def build_message(new_items: list[dict], today_str: str) -> str | None:
    """Build a structured markdown message for WeChat Work.

    Structure (inspired by internal-comms newsletter + 3P patterns):
      Header  — title bar with date and count
      Digest  — 100-200 char executive summary
      Sections — grouped by category, emoji headers, top items with links
      Footer  — website link
    """
    if not new_items:
        return None

    groups = _group_by_section(new_items)
    total = len(new_items)
    major_count = sum(1 for n in new_items if n.get("is_major"))
    digest = _build_digest(groups, total)

    lines = [
        f"📰 **菲律宾金融科技日报 | {today_str}**",
        f"新增<font color=\"info\">{total}</font>条",
    ]
    if major_count:
        lines[-1] += f"　其中<font color=\"warning\">{major_count}条重大</font>"
    lines.append("")
    lines.append(f"> {digest}")
    lines.append("")

    item_no = 0
    for sec, items in groups.items():
        meta = _meta(sec)
        lines.append(f"{meta['emoji']} **{meta['label']}**（{len(items)}条）")
        for item in items[:2]:
            item_no += 1
            title = _truncate(_title_text(item), 45)
            url = item.get("url", "")
            major_tag = "🔴 " if item.get("is_major") else ""
            summary = _truncate(
                item.get("summary_zh") or item.get("summary", ""), 55
            )
            link_part = f"[{title}]({url})" if url else title
            lines.append(f"  {major_tag}{item_no}. {link_part}")
            if summary:
                lines.append(f"  > {summary}")
        if len(items) > 2:
            lines.append(f"  ...另有{len(items) - 2}条")
        lines.append("")

    lines.append(f"[🌐 查看完整日报]({WEBSITE_URL})")

    return "\n".join(lines)


def send_wechat_notification(new_items: list[dict], today_str: str) -> bool:
    """Send a WeChat Work webhook notification with today's new articles.
    Returns True if sent successfully, False otherwise.
    Skips silently if there are no new items."""
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
