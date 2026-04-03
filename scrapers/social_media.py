"""Social media scraper — Reddit via public RSS / JSON feeds."""

from __future__ import annotations

import html
import re
import time
from typing import Generator
from urllib.parse import quote_plus

import requests

from utils import Article, log, truncate

_TAG_RE = re.compile(r"<[^>]+>")
_USER_AGENT = "NewsClippingBot/1.0 (Educational Project)"

_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": _USER_AGENT})
    return _SESSION


def _strip_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


# ---------------------------------------------------------------------------
# Reddit (public JSON API — no auth required for read-only)
# ---------------------------------------------------------------------------

def scrape_reddit(
    *,
    subreddits: list[str],
    keywords: list[str] | None = None,
    max_per_sub: int = 10,
) -> Generator[Article, None, None]:
    """Yield articles from Reddit subreddits, optionally filtered by keywords.

    Uses the public ``.json`` endpoint which returns up to 25 posts without
    authentication.
    """
    seen: set[str] = set()
    session = _get_session()
    keywords = keywords or []

    for sub in subreddits:
        sub = sub.strip().lstrip("/r/").lstrip("r/")
        if not sub:
            continue

        # If keywords are provided, search within the subreddit
        if keywords:
            for kw in keywords:
                url = (
                    f"https://www.reddit.com/r/{sub}/search.json"
                    f"?q={quote_plus(kw)}&restrict_sr=on&sort=new&limit={max_per_sub}"
                )
                yield from _fetch_reddit_json(session, url, sub, kw, max_per_sub, seen)
                time.sleep(1.0)  # Reddit rate limit: ~1 req/sec
        else:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={max_per_sub}"
            yield from _fetch_reddit_json(session, url, sub, "", max_per_sub, seen)
            time.sleep(1.0)


def _fetch_reddit_json(
    session: requests.Session,
    url: str,
    subreddit: str,
    keyword: str,
    limit: int,
    seen: set[str],
) -> Generator[Article, None, None]:
    """Fetch a Reddit JSON endpoint and yield Article objects."""
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        log.error("Reddit fetch failed for r/%s: %s", subreddit, exc)
        return
    except ValueError:
        log.error("Reddit returned invalid JSON for r/%s", subreddit)
        return

    children = data.get("data", {}).get("children", [])
    count = 0

    for child in children:
        if count >= limit:
            break

        post = child.get("data", {})
        permalink = post.get("permalink", "")
        full_url = f"https://www.reddit.com{permalink}" if permalink else post.get("url", "")

        if not full_url or full_url in seen:
            continue
        seen.add(full_url)

        title = html.unescape(post.get("title", "No Title"))
        selftext = post.get("selftext", "")
        summary = truncate(_strip_html(selftext), 200) if selftext else ""

        # Use score and comment count as additional context
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        meta = f"↑{score}  💬{num_comments}"

        yield Article(
            title=title,
            url=full_url,
            source=f"Reddit r/{subreddit}",
            summary=f"{summary}  [{meta}]" if summary else f"[{meta}]",
            published=_unix_to_str(post.get("created_utc", 0)),
            category=subreddit,
            keyword=keyword,
            timestamp=float(post.get("created_utc", 0)),
        )
        count += 1

    log.info("Reddit r/%s: parsed %d posts", subreddit, count)


def _unix_to_str(ts: float) -> str:
    """Convert a UNIX timestamp to a readable string."""
    if not ts:
        return ""
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (OSError, ValueError):
        return ""
