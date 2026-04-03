"""Scraper sub-package — exposes a unified ``run_all_scrapers`` generator."""

from __future__ import annotations

import gc
from typing import Any, Generator

from utils import Article, log


def run_all_scrapers(cfg: dict[str, Any]) -> Generator[Article, None, None]:
    """Yield articles from every enabled source, one at a time.

    Each scraper module is imported lazily and its results are yielded
    as a generator so that only one batch of articles is held in memory
    at any given time.
    """
    max_per_source: int = cfg.get("max_articles_per_source", 10)
    keywords: list[str] = cfg.get("keywords", [])
    categories: list[str] = cfg.get("categories", [])
    sources = cfg.get("sources", {})

    from datetime import datetime
    date_cfg = cfg.get("date_range", {})
    filter_enabled = date_cfg.get("enabled", False)
    start_ts = 0.0
    end_ts = float('inf')
    if filter_enabled:
        s_date = date_cfg.get("start", "")
        e_date = date_cfg.get("end", "")
        if s_date:
            try:
                start_ts = datetime.strptime(s_date, "%Y-%m-%d").timestamp()
            except ValueError:
                pass
        if e_date:
            try:
                dt = datetime.strptime(e_date, "%Y-%m-%d")
                end_ts = datetime(dt.year, dt.month, dt.day, 23, 59, 59).timestamp()
            except ValueError:
                pass

    def _should_yield(art: Article) -> bool:
        if not filter_enabled:
            return True
        if art.timestamp == 0.0:
            return True # Keep if parse failed
        return start_ts <= art.timestamp <= end_ts

    # --- Google News ----------------------------------------------------------
    gn_cfg = sources.get("google_news", {})
    if gn_cfg.get("enabled", True):
        log.info("Scraping Google News …")
        from scrapers.google_news import scrape_google_news
        count = 0
        for article in scrape_google_news(
            keywords=keywords,
            categories=categories,
            language=gn_cfg.get("language", "zh-TW"),
            region=gn_cfg.get("region", "TW"),
            max_per_query=max_per_source,
        ):
            if _should_yield(article):
                yield article
                count += 1
        log.info("Google News: yielded %d articles", count)
        gc.collect()

    # --- Custom RSS feeds -----------------------------------------------------
    rss_cfg = sources.get("rss_feeds", {})
    if rss_cfg.get("enabled", True) and rss_cfg.get("urls"):
        log.info("Scraping RSS feeds …")
        from scrapers.rss_scraper import scrape_rss_feeds
        count = 0
        for article in scrape_rss_feeds(
            feed_urls=rss_cfg["urls"],
            max_per_feed=max_per_source,
            max_summary_length=cfg.get("max_summary_length", 200),
        ):
            if _should_yield(article):
                yield article
                count += 1
        log.info("RSS feeds: yielded %d articles", count)
        gc.collect()

    # --- Reddit ---------------------------------------------------------------
    reddit_cfg = sources.get("reddit", {})
    if reddit_cfg.get("enabled", True) and reddit_cfg.get("subreddits"):
        log.info("Scraping Reddit …")
        from scrapers.social_media import scrape_reddit
        count = 0
        for article in scrape_reddit(
            subreddits=reddit_cfg["subreddits"],
            keywords=keywords,
            max_per_sub=max_per_source,
        ):
            if _should_yield(article):
                yield article
                count += 1
        log.info("Reddit: yielded %d articles", count)
        gc.collect()
