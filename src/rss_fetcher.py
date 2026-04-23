"""Fetch and parse RSS feeds."""

import logging
from dataclasses import dataclass

import feedparser
import requests

from src.config import Config
from src.state_manager import StateManager

logger = logging.getLogger(__name__)

TIMEOUT = 30  # seconds


@dataclass
class FeedEntry:
    source: str
    title: str
    link: str
    summary: str
    id: str


def fetch_all(state: StateManager) -> list[FeedEntry]:
    """Iterate configured RSS sources and return new (unprocessed) entries."""
    entries: list[FeedEntry] = []
    for source in Config.RSS_SOURCES:
        try:
            raw = _fetch_feed(source["url"])
            for item in raw:
                entry = _parse_item(item, source["name"])
                if entry is not None and not state.is_processed(entry.id):
                    entries.append(entry)
        except Exception:
            logger.exception("Failed to fetch RSS from %s (%s)", source["name"], source["url"])
    logger.info("Fetched %d new entries from %d sources", len(entries), len(Config.RSS_SOURCES))
    return entries


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _fetch_feed(url: str) -> list[dict]:
    """Download and parse a single RSS feed.

    Returns the raw *entries* list from feedparser.
    """
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "ai-news-crawler/1.0"})
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    return parsed.entries  # type: ignore[no-any-return]


def _parse_item(item: dict, source_name: str) -> FeedEntry | None:
    """Convert a feedparser entry dict into a FeedEntry.

    Returns ``None`` when the entry lacks essential fields.
    """
    title = _get(item, "title")
    link = _get(item, "link")
    summary = _get(item, "summary") or _get(item, "description") or ""
    entry_id = _get(item, "id") or link or title

    if not title or not link:
        return None

    # Truncate overly long summaries
    summary = summary[:800]

    return FeedEntry(
        source=source_name,
        title=title,
        link=link,
        summary=summary,
        id=entry_id,
    )


def _get(item: dict, key: str) -> str:
    """Safely extract a string value from a feedparser entry."""
    val = item.get(key)
    if val is None:
        return ""
    return str(val)
