"""
HTML page generator using Jinja2 templates.
"""
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import (
    DATA_DIR,
    OUTPUT_DIR,
    PAGES_DIR,
    SECTION_DISPLAY_NAMES,
    SECTION_PAGES,
    SECTION_TAG_CLASSES,
    TEMPLATE_DIR,
)

logger = logging.getLogger(__name__)


def _validate_news_items(news_items: list[dict]) -> list[dict]:
    """Validate and filter news items before page generation.

    Checks:
    1. published date must be valid YYYY-MM-DD format, >= 2026-01-01
    2. If URL contains /YYYY/ where YYYY < 2026, reject item
    3. If published == fetched_date and title/summary mentions pre-2026
       year (not as a reference to data), flag as suspicious
    4. Items without published date are removed
    """
    valid = []
    removed_count = 0

    for item in news_items:
        pub = item.get("published", "")
        url = item.get("url", "")
        title = (item.get("title_zh") or item.get("title", ""))

        # Check 1: published date format & range
        if not pub or len(pub) != 10:
            logger.warning(f"VALIDATION: removed (no/bad date): {title[:50]}")
            removed_count += 1
            continue

        try:
            pub_dt = datetime.strptime(pub, "%Y-%m-%d")
            if pub_dt.year < 2026:
                logger.warning(
                    f"VALIDATION: removed (pre-2026 date {pub}): {title[:50]}"
                )
                removed_count += 1
                continue
        except ValueError:
            logger.warning(f"VALIDATION: removed (invalid date {pub}): {title[:50]}")
            removed_count += 1
            continue

        # Check 2: URL contains year path that contradicts published year
        url_year_matches = re.findall(r"/(\d{4})/", url)
        if url_year_matches:
            url_year = int(url_year_matches[-1])
            if url_year < 2026 and url_year != pub_dt.year:
                # URL says 2024 but published says 2026 — suspicious
                # But allow if URL year is close (e.g., review article)
                if abs(pub_dt.year - url_year) > 1:
                    logger.warning(
                        f"VALIDATION: removed (URL year {url_year} vs pub {pub}): "
                        f"{title[:50]}"
                    )
                    removed_count += 1
                    continue

        # Check 3: published == fetched and content mentions old years
        fetch = item.get("fetched_date", "")
        if pub == fetch:
            summary = item.get("summary_zh") or item.get("summary", "")
            combined = title + " " + summary
            old_years_in_text = [
                int(y) for y in re.findall(r"20[12]\d", combined) if int(y) < 2025
            ]
            if old_years_in_text:
                # The text primarily discusses events from years before 2025
                # but claims to be published today — mark as suspicious but keep
                logger.info(
                    f"VALIDATION: suspicious (text mentions {old_years_in_text}, "
                    f"pub={pub}, fetch={fetch}): {title[:50]}"
                )

        valid.append(item)

    if removed_count:
        logger.warning(f"VALIDATION: removed {removed_count} invalid items")
    else:
        logger.info(f"VALIDATION: all {len(valid)} items passed date checks")

    return valid


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )


def _load_all_news(data_dir: Path) -> list[dict]:
    news_file = data_dir / "news.json"
    if not news_file.exists():
        return []
    with open(news_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_key_points() -> dict:
    """Load curated key-points per section from JSON config."""
    kp_file = DATA_DIR / "key_points.json"
    if not kp_file.exists():
        return {}
    try:
        with open(kp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load key_points.json: {e}")
        return {}


def generate_all_pages(news_items: list[dict], vol_number: int = 1):
    """Generate/update all HTML pages from news data."""
    news_items = _validate_news_items(news_items)

    env = _get_env()
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    context = {
        "today_str": today.strftime("%Y-%m-%d"),
        "today_day": today.strftime("%a"),
        "yesterday_str": yesterday.strftime("%Y-%m-%d"),
        "yesterday_day": yesterday.strftime("%a"),
        "month_str": today.strftime("%Y年%m月"),
        "vol": f"Vol.{vol_number:03d}",
        "section_pages": SECTION_PAGES,
        "section_tags": SECTION_TAG_CLASSES,
        "section_names": SECTION_DISPLAY_NAMES,
    }

    # Group news by section
    sections = {key: [] for key in SECTION_PAGES}
    for item in news_items:
        for sec in item.get("sections", []):
            if sec in sections:
                sections[sec].append(item)

    # Sort each section by date (newest first)
    for sec in sections:
        sections[sec].sort(key=lambda x: x.get("published", ""), reverse=True)

    # Today's and yesterday's news
    today_news = [
        n for n in news_items if n.get("published") == today.strftime("%Y-%m-%d")
    ]
    yesterday_news = [
        n for n in news_items if n.get("published") == yesterday.strftime("%Y-%m-%d")
    ]

    # Current month news
    month_prefix = today.strftime("%Y-%m")
    monthly_news = [
        n for n in news_items if n.get("published", "").startswith(month_prefix)
    ]
    monthly_news.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Major news (top 5)
    major_news = [n for n in news_items if n.get("is_major")][:5]

    # Monthly major: prioritize is_major items, then most recent
    monthly_major = [n for n in monthly_news if n.get("is_major")]
    if len(monthly_major) < 5:
        remaining = [n for n in monthly_news if not n.get("is_major")]
        monthly_major.extend(remaining[: 5 - len(monthly_major)])

    context.update(
        {
            "sections": sections,
            "today_news": today_news,
            "yesterday_news": yesterday_news,
            "monthly_news": monthly_news,
            "monthly_major": monthly_major,
            "major_news": major_news,
            "all_news": news_items,
        }
    )

    # Generate each page
    template_files = {
        "index.html": OUTPUT_DIR / "index.html",
        "section.html": None,  # template used per-section
        "yesterday.html": PAGES_DIR / "yesterday.html",
        "monthly.html": PAGES_DIR / "monthly.html",
    }

    # 1. Index page
    _render_template(env, "index.html", OUTPUT_DIR / "index.html", context)

    # 2. Section pages (skip curated pages marked with <!-- CURATED -->)
    all_key_points = _load_key_points()

    for sec_key, page_file in SECTION_PAGES.items():
        output_path = PAGES_DIR / page_file
        if output_path.exists():
            try:
                content = output_path.read_text(encoding="utf-8")
                if "<!-- CURATED -->" in content:
                    logger.info(f"Skipping curated page: {page_file}")
                    continue
            except Exception:
                pass

        sec_context = {
            **context,
            "section_key": sec_key,
            "section_name": SECTION_DISPLAY_NAMES.get(sec_key, sec_key),
            "section_news": sections.get(sec_key, []),
            "page_file": page_file,
            "key_points": all_key_points.get(sec_key),
        }
        _render_template(
            env, "section.html", PAGES_DIR / page_file, sec_context
        )

    # 3. Yesterday page
    _render_template(
        env, "yesterday.html", PAGES_DIR / "yesterday.html", context
    )

    # 4. Monthly page
    _render_template(
        env, "monthly.html", PAGES_DIR / "monthly.html", context
    )

    logger.info(f"Generated all HTML pages. Vol: {context['vol']}")


def _render_template(env: Environment, template_name: str, output_path: Path, context: dict):
    """Render a Jinja2 template to file."""
    try:
        template = env.get_template(template_name)
        html = template.render(**context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.debug(f"Generated: {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate {output_path}: {e}")


def get_next_vol_number() -> int:
    """Determine the next volume number from existing data."""
    from config import DATA_DIR

    vol_file = DATA_DIR / "vol_counter.txt"
    if vol_file.exists():
        current = int(vol_file.read_text().strip())
    else:
        current = 0
    next_vol = current + 1
    vol_file.parent.mkdir(parents=True, exist_ok=True)
    vol_file.write_text(str(next_vol))
    return next_vol
