"""Fetch and parse RSS feeds."""

import html
import logging
from dataclasses import dataclass

import feedparser
import requests
from bs4 import BeautifulSoup

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


def clean_html_content(raw_content: str) -> str:
    """清理 RSS 中的 HTML 标签和转义字符，只保留纯文本。"""
    if not raw_content:
        return ""
    
    # 1. 把 &lt; 还原成 < 等正常的 HTML 标签
    unescaped_text = html.unescape(raw_content)
    
    # 2. 用 BeautifulSoup 剥离所有 HTML 标签，只留下纯文字
    soup = BeautifulSoup(unescaped_text, "html.parser")
    clean_text = soup.get_text(separator=" ", strip=True) 
    
    return clean_text


def fetch_all(state: StateManager) -> list[FeedEntry]:
    """Iterate configured RSS sources and return new (unprocessed) entries.

    Each source is limited to ``Config.MAX_ENTRIES_PER_SOURCE`` items.
    """
    entries: list[FeedEntry] = []
    for source in Config.RSS_SOURCES:
        source_count = 0
        try:
            raw = _fetch_feed(source["url"])
            for item in raw:
                entry = _parse_item(item, source["name"])
                if entry is not None and not state.is_processed(entry.id):
                    entries.append(entry)
                    source_count += 1
                    if source_count >= Config.MAX_ENTRIES_PER_SOURCE:
                        break
        except Exception:
            logger.exception("Failed to fetch RSS from %s (%s)", source["name"], source["url"])
    logger.info(
        "Fetched %d new entries from %d sources (max %d each)",
        len(entries),
        len(Config.RSS_SOURCES),
        Config.MAX_ENTRIES_PER_SOURCE,
    )
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
    raw_summary = _get(item, "summary") or _get(item, "description") or ""
    entry_id = _get(item, "id") or link or title

    if not title or not link:
        return None

    # 调用清洗函数，去除 HTML 杂质
    clean_summary = clean_html_content(raw_summary)

    # Truncate overly long summaries (基于清洗后的纯文本截断)
    clean_summary = clean_summary[:800]

    return FeedEntry(
        source=source_name,
        title=title,
        link=link,
        summary=clean_summary,
        id=entry_id,
    )


def _get(item: dict, key: str) -> str:
    """Safely extract a string value from a feedparser entry."""
    val = item.get(key)
    if val is None:
        return ""
    return str(val)