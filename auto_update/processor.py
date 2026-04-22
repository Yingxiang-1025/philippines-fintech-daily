"""
Content processor: keyword-based section assignment + optional AI summarization.
"""
import logging
from typing import Optional

from config import (
    ENABLE_AI_SUMMARY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    SECTION_KEYWORDS,
)
from fetcher import NewsItem

logger = logging.getLogger(__name__)


def assign_sections(items: list[NewsItem]) -> list[NewsItem]:
    """Assign each news item to one or more sections based on keyword matching."""
    for item in items:
        text = (item.title + " " + item.summary).lower()
        matched = []
        for section, keywords in SECTION_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                matched.append(section)
        item.sections = matched if matched else ["digital_lending"]

        if "akulaku" in text:
            if "akulaku" not in item.sections:
                item.sections.append("akulaku")

    return items


def generate_summaries_zh(items: list[NewsItem]) -> list[NewsItem]:
    """
    Generate Chinese summaries using OpenAI-compatible API.
    Skips if no API key configured.
    """
    if not ENABLE_AI_SUMMARY:
        logger.info("AI summary disabled (no OPENAI_API_KEY). Using original summaries.")
        for item in items:
            if not item.summary_zh:
                item.summary_zh = item.summary
        return items

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    except ImportError:
        logger.warning("openai package not installed. Skipping AI summaries.")
        for item in items:
            item.summary_zh = item.summary
        return items

    for item in items:
        if item.summary_zh:
            continue
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是菲律宾金融科技领域的专业分析师。"
                            "请将以下英文新闻摘要翻译为简洁的中文摘要（2-3句），"
                            "用<strong>标签标记关键数据和要点。"
                            "只输出中文摘要，不要任何额外说明。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"标题: {item.title}\n摘要: {item.summary}",
                    },
                ],
                max_tokens=300,
                temperature=0.3,
            )
            item.summary_zh = resp.choices[0].message.content.strip()
            logger.debug(f"AI summary generated for: {item.title[:50]}")
        except Exception as e:
            logger.warning(f"AI summary failed for '{item.title[:50]}': {e}")
            item.summary_zh = item.summary

    return items


def mark_major_news(items: list[NewsItem], top_n: int = 3) -> list[NewsItem]:
    """
    Mark the top N most important news as major.
    Priority: Akulaku > regulation > funding > product > market.
    """
    priority_keywords = {
        5: ["Akulaku", "akulaku"],
        4: ["regulation", "SEC", "BSP", "moratorium", "ban"],
        3: ["$", "million", "billion", "funding", "raises", "investment"],
        2: ["launch", "introduce", "new product", "partnership"],
        1: ["growth", "market", "report"],
    }

    scored: list[tuple[int, NewsItem]] = []
    for item in items:
        text = item.title + " " + item.summary
        score = 0
        for points, keywords in priority_keywords.items():
            if any(kw in text for kw in keywords):
                score = max(score, points)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    for i, (_, item) in enumerate(scored):
        item.is_major = i < top_n

    return items


def apply_translations(items: list[NewsItem]) -> list[NewsItem]:
    """Translate all NewsItem objects to Chinese (title, summary, source)."""
    from translator import translate_summary, translate_title, translate_source, _looks_garbled

    for item in items:
        needs_summary = (
            not item.summary_zh
            or item.summary_zh == item.summary
            or _looks_garbled(item.summary_zh)
        )
        if needs_summary:
            item.summary_zh = translate_summary(item.summary)

    return items


def process_news(items: list[NewsItem]) -> list[NewsItem]:
    """Full processing pipeline: assign sections → AI summary → translate → mark major."""
    items = assign_sections(items)
    items = generate_summaries_zh(items)
    items = apply_translations(items)
    items = mark_major_news(items)
    return items
