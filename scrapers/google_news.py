"""Google News scraper via public RSS feeds — zero API keys required."""

from __future__ import annotations

import html
import re
import time
from typing import Generator
from urllib.parse import quote_plus

import feedparser
import requests

from utils import Article, GOOGLE_NEWS_CATEGORIES, log, truncate

_SESSION: requests.Session | None = None
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": _USER_AGENT})
    return _SESSION

# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

_BASE = "https://news.google.com/rss"


def _keyword_url(keyword: str, lang: str, region: str) -> str:
    q = quote_plus(keyword)
    ceid = f"{region}:{lang}"
    return f"{_BASE}/search?q={q}&hl={lang}&gl={region}&ceid={ceid}"


def _category_url(topic_id: str, lang: str, region: str) -> str:
    ceid = f"{region}:{lang}"
    return f"{_BASE}/headlines/section/topic/{topic_id}?hl={lang}&gl={region}&ceid={ceid}"


# ---------------------------------------------------------------------------
# HTML tag stripper (avoid importing heavy libs)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_google_news(
    *,
    keywords: list[str],
    categories: list[str],
    language: str = "zh-TW",
    region: str = "TW",
    max_per_query: int = 10,
) -> Generator[Article, None, None]:
    """Yield :class:`Article` objects from Google News RSS feeds.

    Queries are built from *keywords* (free-text search) and *categories*
    (mapped to Google News topic IDs).
    """
    seen_urls: set[str] = set()

    # --- Category feeds -------------------------------------------------------
    for cat in categories:
        topic_id = GOOGLE_NEWS_CATEGORIES.get(cat.lower().strip())
        if not topic_id:
            log.warning("Unknown category '%s', skipping", cat)
            continue

        url = _category_url(topic_id, language, region)
        yield from _parse_feed(url, f"Google News [{cat}]", cat, "", max_per_query, seen_urls)
        time.sleep(0.5)  # polite delay

    # --- Keyword feeds --------------------------------------------------------
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        url = _keyword_url(kw, language, region)
        yield from _parse_feed(url, f"Google News", "", kw, max_per_query, seen_urls)
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _parse_feed(
    feed_url: str,
    source_name: str,
    category: str,
    keyword: str,
    limit: int,
    seen: set[str],
) -> Generator[Article, None, None]:
    """Parse a single RSS feed and yield up to *limit* unseen articles."""
    try:
        session = _get_session()
        resp = session.get(feed_url, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except requests.RequestException as exc:
        log.error("Failed to fetch feed %s: %s", feed_url, exc)
        return
    except Exception as exc:
        log.error("Failed to parse feed %s: %s", feed_url, exc)
        return

    if feed.bozo and not feed.entries:
        log.warning("Feed returned no entries: %s", feed_url)
        return

    count = 0
    for entry in feed.entries:
        if count >= limit:
            break

        link = entry.get("link", "").strip()
        if not link or link in seen:
            continue
        seen.add(link)

        summary_raw = entry.get("summary", "") or entry.get("description", "")
        summary = truncate(_strip_html(summary_raw), 200)

        published = entry.get("published", "") or entry.get("updated", "")
        published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        timestamp = time.mktime(published_parsed) if published_parsed else 0.0

        yield Article(
            title=_strip_html(entry.get("title", "No Title")),
            url=link,
            source=source_name,
            summary=summary,
            published=published,
            category=category,
            keyword=keyword,
            timestamp=timestamp,
        )
        count += 1
