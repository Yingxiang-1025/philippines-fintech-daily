"""
News fetcher module: RSS feeds + web search.
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import feedparser
import requests
from dateutil import parser as date_parser

from config import (
    DATA_DIR,
    GLOBAL_KEYWORDS,
    RSS_FEEDS,
    SEARCH_QUERIES,
    SERPAPI_KEY,
)

logger = logging.getLogger(__name__)


class NewsItem:
    """Represents a single news article."""

    def __init__(
        self,
        title: str,
        url: str,
        summary: str,
        source: str,
        published: Optional[str] = None,
        sections: Optional[list] = None,
        summary_zh: str = "",
        is_major: bool = False,
    ):
        self.title = title
        self.url = url
        self.summary = summary
        self.source = source
        self.published = published or datetime.now().strftime("%Y-%m-%d")
        self.sections = sections or []
        self.summary_zh = summary_zh
        self.is_major = is_major

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "published": self.published,
            "sections": self.sections,
            "summary_zh": self.summary_zh,
            "is_major": self.is_major,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


def fetch_rss_feeds(max_age_days: int = 7) -> list[NewsItem]:
    """Fetch news from configured RSS feeds."""
    items = []
    cutoff = datetime.now() - timedelta(days=max_age_days)

    for feed_config in RSS_FEEDS:
        try:
            logger.info(f"Fetching RSS: {feed_config['name']}...")
            feed = feedparser.parse(feed_config["url"])

            for entry in feed.entries[:20]:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])

                if pub_date and pub_date < cutoff:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Remove HTML tags from summary
                if "<" in summary:
                    from bs4 import BeautifulSoup

                    summary = BeautifulSoup(summary, "html.parser").get_text()
                summary = summary[:500]

                if not _is_relevant(title, summary):
                    continue

                item = NewsItem(
                    title=title,
                    url=link,
                    summary=summary,
                    source=feed_config["name"],
                    published=pub_date.strftime("%Y-%m-%d") if pub_date else None,
                )
                items.append(item)

        except Exception as e:
            logger.warning(f"Failed to fetch RSS from {feed_config['name']}: {e}")

    logger.info(f"RSS: fetched {len(items)} relevant articles")
    return items


def search_web(queries: Optional[list] = None) -> list[NewsItem]:
    """
    Search for news using SerpAPI (Google Search API).
    Falls back to Google News RSS if no API key configured.
    """
    queries = queries or SEARCH_QUERIES
    items = []

    if SERPAPI_KEY:
        items = _search_serpapi(queries)
    else:
        items = _search_google_news_rss(queries)

    logger.info(f"Web search: fetched {len(items)} relevant articles")
    return items


def _search_serpapi(queries: list) -> list[NewsItem]:
    """Use SerpAPI for Google search results."""
    items = []
    seen_urls = set()

    for query in queries:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "engine": "google_news",
                    "gl": "ph",
                    "hl": "en",
                },
                timeout=15,
            )
            data = resp.json()

            for result in data.get("news_results", [])[:5]:
                url = result.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_date = None
                if "date" in result:
                    try:
                        pub_date = date_parser.parse(result["date"]).strftime(
                            "%Y-%m-%d"
                        )
                    except (ValueError, TypeError):
                        pass

                item = NewsItem(
                    title=result.get("title", ""),
                    url=url,
                    summary=result.get("snippet", ""),
                    source=result.get("source", {}).get("name", "Web"),
                    published=pub_date,
                )
                items.append(item)

            time.sleep(1)

        except Exception as e:
            logger.warning(f"SerpAPI search failed for '{query}': {e}")

    return items


def _search_google_news_rss(queries: list) -> list[NewsItem]:
    """Fallback: use Google News RSS (free, no API key needed)."""
    items = []
    seen_urls = set()

    for query in queries:
        try:
            from urllib.parse import quote
            encoded_query = quote(query + " Philippines")
            rss_url = (
                f"https://news.google.com/rss/search?q={encoded_query}&hl=en-PH&gl=PH&ceid=PH:en"
            )
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:5]:
                url = entry.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime(
                        "%Y-%m-%d"
                    )

                item = NewsItem(
                    title=entry.get("title", "").strip(),
                    url=url,
                    summary=entry.get("summary", "").strip()[:500],
                    source=entry.get("source", {}).get("title", "Google News"),
                    published=pub_date,
                )
                items.append(item)

            time.sleep(0.5)

        except Exception as e:
            logger.warning(f"Google News RSS search failed for '{query}': {e}")

    return items


def _is_relevant(title: str, summary: str) -> bool:
    """Check if article is relevant to Philippines fintech.
    Requires at least 2 keyword matches to reduce noise from general business feeds."""
    text = (title + " " + summary).lower()
    matches = sum(1 for kw in GLOBAL_KEYWORDS if kw.lower() in text)
    return matches >= 2


def load_existing_news() -> list[dict]:
    """Load previously saved news from JSON file."""
    news_file = DATA_DIR / "news.json"
    if news_file.exists():
        with open(news_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_news(items: list[dict]):
    """Save news items to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    news_file = DATA_DIR / "news.json"
    with open(news_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(items)} news items to {news_file}")


def deduplicate(new_items: list[NewsItem], existing: list[dict]) -> list[NewsItem]:
    """Remove duplicates based on URL."""
    existing_urls = {item["url"] for item in existing}
    return [item for item in new_items if item.url not in existing_urls]
