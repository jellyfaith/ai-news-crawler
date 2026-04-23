"""Fetch and extract article plain text from URLs (RAG source material)."""

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TIMEOUT = 20
MAX_CHARS = 5000
_USER_AGENT = "Mozilla/5.0 (compatible; ai-news-crawler/1.0)"


def fetch_article(url: str) -> str:
    """Download *url*, strip HTML, return clean plain text.

    Up to ``MAX_CHARS`` characters.  Returns empty string on any failure
    so the caller can gracefully fall back to the RSS summary.
    """
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()

        # Detect encoding from headers or content
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip non-content tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = text[:MAX_CHARS]
        logger.debug("Fetched %d chars from %s", len(text), url)
        return text

    except Exception:
        logger.warning("Failed to fetch article from %s (will fall back to RSS summary)", url)
        return ""
