"""Generic RSS feed scraper — handles any valid RSS / Atom feed URL."""

from __future__ import annotations

import html
import re
import time
from typing import Generator

import feedparser
import requests

from utils import Article, log, truncate

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": _USER_AGENT})
    return _SESSION

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


def _extract_source(feed: feedparser.FeedParserDict, url: str) -> str:
    """Try to derive a human-readable source name from the feed metadata."""
    title = feed.feed.get("title", "").strip()
    if title:
        return title
    # Fallback: domain from URL
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return url


def scrape_rss_feeds(
    *,
    feed_urls: list[str],
    max_per_feed: int = 10,
    max_summary_length: int = 200,
) -> Generator[Article, None, None]:
    """Yield articles from a list of RSS/Atom feed URLs."""
    seen_urls: set[str] = set()

    for feed_url in feed_urls:
        feed_url = feed_url.strip()
        if not feed_url:
            continue

        try:
            session = _get_session()
            resp = session.get(feed_url, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except requests.RequestException as exc:
            log.error("RSS fetch failed for %s: %s", feed_url, exc)
            continue
        except Exception as exc:
            log.error("RSS parse failed for %s: %s", feed_url, exc)
            continue

        if feed.bozo and not feed.entries:
            log.warning("RSS feed returned no entries: %s", feed_url)
            continue

        source_name = _extract_source(feed, feed_url)
        count = 0

        for entry in feed.entries:
            if count >= max_per_feed:
                break

            link = entry.get("link", "").strip()
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)

            title = _strip_html(entry.get("title", "No Title"))
            summary_raw = entry.get("summary", "") or entry.get("description", "")
            summary = truncate(_strip_html(summary_raw), max_summary_length)
            published = entry.get("published", "") or entry.get("updated", "")
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            timestamp = time.mktime(published_parsed) if published_parsed else 0.0

            # Try to extract category tags from the entry
            cat_tags = entry.get("tags", [])
            category = cat_tags[0].get("term", "") if cat_tags else ""

            yield Article(
                title=title,
                url=link,
                source=source_name,
                summary=summary,
                published=published,
                category=category,
                keyword="",
                timestamp=timestamp,
            )
            count += 1

        log.info("RSS [%s]: parsed %d articles", source_name, count)
        time.sleep(0.3)
