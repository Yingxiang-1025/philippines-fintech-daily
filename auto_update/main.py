"""
Philippines Fintech Daily Brief — Auto Updater

Usage:
    python main.py              # Run once: fetch, process, generate
    python main.py --schedule   # Run daily at 08:00 (daemon mode)
    python main.py --dry-run    # Fetch & process only, no HTML generation

Environment variables:
    OPENAI_API_KEY    – OpenAI API key for Chinese summaries (optional)
    OPENAI_BASE_URL   – Custom API base URL (optional, for compatible APIs)
    OPENAI_MODEL      – Model name (default: gpt-4o-mini)
    SERPAPI_KEY        – SerpAPI key for web search (optional, falls back to Google News RSS)
"""
import argparse
import logging
import sys
from datetime import datetime

import config
from fetcher import (
    NewsItem,
    deduplicate,
    fetch_rss_feeds,
    load_existing_news,
    save_news,
    search_web,
)
from generator import generate_all_pages, get_next_vol_number
from processor import process_news

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def run_update(dry_run: bool = False):
    """Execute one full update cycle."""
    logger.info("=" * 60)
    logger.info(f"Starting daily update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    # 1. Load existing news (merge seed data on first run)
    existing = load_existing_news()
    if not existing:
        seed_file = config.DATA_DIR / "seed_news.json"
        if seed_file.exists():
            import json as _json
            with open(seed_file, "r", encoding="utf-8") as f:
                existing = _json.load(f)
            logger.info(f"Loaded {len(existing)} seed news items")
    logger.info(f"Existing news items: {len(existing)}")

    # 2. Fetch new articles
    rss_items = fetch_rss_feeds(max_age_days=7)
    search_items = search_web()
    all_new = rss_items + search_items
    logger.info(f"Fetched {len(all_new)} new articles (RSS: {len(rss_items)}, Search: {len(search_items)})")

    # 3. Deduplicate
    unique_new = deduplicate(all_new, existing)
    logger.info(f"After dedup: {len(unique_new)} new unique articles")

    if not unique_new:
        logger.info("No new articles found. Skipping update.")
        return

    # 4. Process (assign sections, AI summary, mark major)
    processed = process_news(unique_new)
    logger.info(f"Processed {len(processed)} articles")

    # 5. Merge with existing — stamp fetched_date on new items
    today_stamp = datetime.now().strftime("%Y-%m-%d")
    new_dicts = [item.to_dict() for item in processed]
    for nd in new_dicts:
        nd["fetched_date"] = today_stamp
    for ex in existing:
        if "fetched_date" not in ex:
            ex["fetched_date"] = ex.get("published", today_stamp)
    all_news = new_dicts + existing

    # Keep only last 90 days of news
    cutoff = (datetime.now().replace(day=1)).strftime("%Y-%m-%d")
    # Actually keep 3 months of history
    from dateutil.relativedelta import relativedelta
    cutoff_date = datetime.now() - relativedelta(months=3)
    cutoff = cutoff_date.strftime("%Y-%m-%d")
    all_news = [n for n in all_news if n.get("published", "9999") >= cutoff]

    # 6. Apply translations to ALL items (including existing)
    from translator import translate_news_item
    logger.info(f"Translating {len(all_news)} items to Chinese...")
    for i, n in enumerate(all_news):
        translate_news_item(n)
        if (i + 1) % 10 == 0:
            logger.info(f"  translated {i + 1}/{len(all_news)}")
    logger.info("Translation complete.")

    # 7. Save
    save_news(all_news)
    logger.info(f"Total news items in database: {len(all_news)}")

    # 8. Generate HTML
    if not dry_run:
        vol = get_next_vol_number()
        generate_all_pages(all_news, vol_number=vol)
        logger.info(f"HTML pages generated. Volume: {vol:03d}")
    else:
        logger.info("Dry run mode: HTML generation skipped.")

    # 9. Summary
    section_counts = {}
    for item in new_dicts:
        for sec in item.get("sections", []):
            section_counts[sec] = section_counts.get(sec, 0) + 1
    logger.info("New articles by section:")
    for sec, count in sorted(section_counts.items()):
        logger.info(f"  {config.SECTION_DISPLAY_NAMES.get(sec, sec)}: {count}")

    major_count = sum(1 for n in new_dicts if n.get("is_major"))
    logger.info(f"Major news items: {major_count}")
    logger.info("Update complete!")


def run_scheduled():
    """Run the updater on a daily schedule."""
    import schedule
    import time

    logger.info("Starting scheduled mode. Will run daily at 08:00.")
    logger.info("Press Ctrl+C to stop.")

    # Run once immediately
    run_update()

    # Schedule daily at 08:00
    schedule.every().day.at("08:00").do(run_update)

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="Philippines Fintech Daily Brief Auto Updater"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in daemon mode, updating daily at 08:00",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and process only, do not generate HTML",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        run_update(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
