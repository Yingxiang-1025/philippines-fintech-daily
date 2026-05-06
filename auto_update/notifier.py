"""
WeChat Work (企业微信) webhook notification for daily news updates.
Sends a markdown-formatted summary of new articles, prioritized by:
  Akulaku > Regulation > Others
"""
import logging
import requests

logger = logging.getLogger(__name__)

WECHAT_WEBHOOK_URL = (
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    "?key=dd8952d8-8721-40e1-a674-b80d65a229ca"
)

SECTION_PRIORITY = {
    "akulaku": 0,
    "regulation": 1,
    "credit_card": 2,
    "digital_lending": 3,
    "cash_loan": 4,
    "bnpl": 5,
    "digital_bank": 6,
}


def _priority_key(item: dict) -> int:
    """Return the highest priority (lowest number) among the item's sections."""
    sections = item.get("sections", [])
    return min((SECTION_PRIORITY.get(s, 99) for s in sections), default=99)


def _section_label(item: dict) -> str:
    """Return the display label for the item's highest-priority section."""
    labels = {
        "akulaku": "Akulaku",
        "regulation": "监管动态",
        "credit_card": "信用卡",
        "digital_lending": "数字信贷",
        "cash_loan": "现金贷",
        "bnpl": "BNPL",
        "digital_bank": "数字银行",
    }
    sections = item.get("sections", [])
    if not sections:
        return "金融科技"
    best = min(sections, key=lambda s: SECTION_PRIORITY.get(s, 99))
    return labels.get(best, "金融科技")


def _truncate(text: str, max_len: int = 80) -> str:
    if not text:
        return ""
    clean = text.replace("\n", " ").strip()
    if "<" in clean:
        from bs4 import BeautifulSoup
        clean = BeautifulSoup(clean, "html.parser").get_text()
    return clean[:max_len] + "..." if len(clean) > max_len else clean


def _build_digest(sorted_items: list[dict]) -> str:
    """Build a readable narrative digest (100-200 chars) from actual news."""
    sentences = []
    seen_sections = set()
    for item in sorted_items:
        best_sec = min(
            item.get("sections", ["other"]),
            key=lambda s: SECTION_PRIORITY.get(s, 99),
        )
        if best_sec in seen_sections:
            continue
        seen_sections.add(best_sec)

        summary = item.get("summary_zh") or item.get("summary", "")
        title = item.get("title_zh") or item.get("title", "")
        raw = title.split("】")[-1].strip() if "】" in title else title
        raw = raw.replace("\n", "").strip()

        brief = _truncate(summary, 50) if summary else _truncate(raw, 40)
        label = _section_label(item)
        sentences.append(f"{label}方面，{brief}")

        if len("。".join(sentences)) >= 160:
            break

    result = "。".join(sentences)
    if len(result) > 200:
        result = result[:197] + "…"
    if not result.endswith("。"):
        result += "。"
    return result


def build_message(new_items: list[dict], today_str: str) -> str | None:
    """Build a two-part markdown message for WeChat Work webhook.
    Part 1: Substantive digest summary (50-100 chars)
    Part 2: News list with brief + link
    Returns None if no items to send."""
    if not new_items:
        return None

    sorted_items = sorted(new_items, key=_priority_key)
    digest = _build_digest(sorted_items)

    lines = [
        f"**📰 菲律宾金融科技日报 | {today_str}**",
        f"新增 {len(sorted_items)} 条资讯",
        "",
        f"> **今日要点：**{digest}",
        "",
    ]

    show_count = min(len(sorted_items), 5)
    for i, item in enumerate(sorted_items[:show_count], 1):
        label = _section_label(item)
        title_raw = item.get("title_zh") or item.get("title", "")
        title = title_raw.split("】")[-1].strip() if "】" in title_raw else title_raw
        title = _truncate(title, 50)
        brief = _truncate(item.get("summary_zh") or item.get("summary", ""), 60)
        url = item.get("url", "")
        major = "🔴 " if item.get("is_major") else ""

        lines.append(f"**{major}{i}. [{label}] {title}**")
        if brief:
            lines.append(f"> {brief}")
        if url:
            lines.append(f"[原文链接]({url})")
        lines.append("")

    if len(sorted_items) > show_count:
        lines.append(f"...另有 {len(sorted_items) - show_count} 条资讯")
        lines.append("")

    lines.append(
        "[🌐 查看完整网站](https://yingxiang-1025.github.io/ph-fintech-daily/)"
    )

    return "\n".join(lines)


def send_wechat_notification(new_items: list[dict], today_str: str) -> bool:
    """Send a WeChat Work webhook notification with today's new articles.
    Returns True if sent successfully, False otherwise.
    Does NOT send if there are no new items."""
    if not new_items:
        logger.info("No new items today. Skipping WeChat notification.")
        return False

    message = build_message(new_items, today_str)
    if not message:
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": message,
        },
    }

    try:
        resp = requests.post(WECHAT_WEBHOOK_URL, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info(
                f"WeChat notification sent: {len(new_items)} items"
            )
            return True
        else:
            logger.warning(
                f"WeChat webhook returned error: {result.get('errmsg', 'unknown')}"
            )
            return False
    except Exception as e:
        logger.error(f"WeChat notification failed: {e}")
        return False
