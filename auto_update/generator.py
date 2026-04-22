"""
HTML page generator using Jinja2 templates.
"""
import json
import logging
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
