"""Shared utilities and data structures for News Clipping Tool."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

def _get_appdata_dir() -> str:
    # Use %LOCALAPPDATA% if available, else fallback to user home
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        local_appdata = os.path.expanduser("~")
    app_dir = os.path.join(local_appdata, "NewsClippingTool")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

# Point base directly to hidden app data to keep desktop/folders clean
BASE_DIR = _get_appdata_dir()

CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

# Common fallback mappings for news categories to standard strings.
CAT_MAP: dict[str, str] = {
    "tech": "technology",
    "business": "business",
    "finance": "business",
    "politics": "politics",
    "world": "world",
    "sports": "sports",
    "entertainment": "entertainment",
    "health": "health",
    "science": "science",
}

PRESET_CATEGORIES = [
    ("科技 Technology", "technology"),
    ("商業 Business", "business"),
    ("政治 Politics", "politics"),
    ("娛樂 Entertainment", "entertainment"),
    ("體育 Sports", "sports"),
    ("健康 Health", "health"),
    ("科學 Science", "science"),
    ("全球 World", "world"),
]

GOOGLE_NEWS_CATEGORIES: dict[str, str] = {
    "technology": "TECHNOLOGY",
    "business": "BUSINESS",
    "science": "SCIENCE",
    "health": "HEALTH",
    "sports": "SPORTS",
    "entertainment": "ENTERTAINMENT",
    "world": "WORLD",
    "politics": "NATION",
}

def truncate(text: str, max_len: int) -> str:
    """Truncate a string to *max_len* safely."""
    return text[:max_len] + "..." if len(text) > max_len else text

# ---------------------------------------------------------------------------
# I18N Translation System
# ---------------------------------------------------------------------------
_I18N = {
    # UI
    "ui_title": {"zh": "新聞追蹤小幫手 - 設定介面", "en": "News Clipping Tool - Settings"},
    "ui_header": {"zh": "設定您的每日閱報規則", "en": "Configure Your Daily News Rules"},
    "sys_settings": {"zh": "⚙️ 系統設定", "en": "⚙️ System Settings"},
    "autostart": {"zh": "讓小幫手隨著電腦開機自動啟動 (強烈建議)", "en": "Run automatically on startup (Recommended)"},
    "output_dir": {"zh": "新聞報表儲存位置:", "en": "News Report Output Folder:"},
    "browse": {"zh": "📂 瀏覽", "en": "📂 Browse"},
    "schedule_title": {"zh": "⏰ 自訂每日推播時間", "en": "⏰ Custom Daily Schedule"},
    "schedule_sub": {"zh": "當時間一到，我們將在右下角通知您，並自動以網頁開啟精華新聞。", "en": "At the set time, we will notify you and open the news summary in your browser."},
    "add_time": {"zh": "新增時間 +", "en": "Add Time +"},
    "no_time": {"zh": "(目前未設定任何時間)", "en": "(No time specified)"},
    "content_title": {"zh": "📰 關注哪些內容？", "en": "📰 What to Follow?"},
    "keywords_lbl": {"zh": "追蹤特定關鍵字 (請用半形逗號 , 分隔，如：台積電, AI):", "en": "Track Keywords (comma separated, e.g. space, AI):"},
    "btn_save": {"zh": "儲存並套用", "en": "Save & Apply"},
    "btn_cancel": {"zh": "取消", "en": "Cancel"},
    "warn_time": {"zh": "請至少新增一個提醒時間！", "en": "Please add at least one notification time!"},
    "save_success": {"zh": "🎉 設定已儲存成功！\n新聞小幫手將會在背景運作，並於指定時間產生新聞。", "en": "🎉 Settings Saved!\nThe background process will generate news reports at configured times."},
    "save_title": {"zh": "儲存成功", "en": "Success"},
    "language_lbl": {"zh": "🌍 介面與報表語言 / Language:", "en": "🌍 UI & Report Language:"},
    "date_filter_title": {"zh": "📅 指定新聞擷取日期範圍", "en": "📅 Specific Date Range"},
    "date_filter_enable": {"zh": "啟用指定日期擷取", "en": "Enable specific date range"},
    "start_date": {"zh": "開始日期:", "en": "Start Date:"},
    "end_date": {"zh": "結束日期:", "en": "End Date:"},

    # Notification & Output
    "notif_title": {"zh": "📰 新聞小幫手", "en": "📰 News Clipping"},
    "notif_fetching": {"zh": "正在為您擷取各方新聞，請稍候...", "en": "Fetching news from all sources, please wait..."},
    "notif_msg": {"zh": "為您整理好的 {t} 篇新聞已經準備好囉！即將為您開啟。", "en": "{t} daily news articles are ready! Opening now."},
    "report_title": {"zh": "今日新聞精華", "en": "Daily News Summary"},
    "report_sub": {"zh": "{d} — 共為您整理了 {t} 篇新聞", "en": "{d} — {t} articles collected"},
    "report_footer": {"zh": "由 <a href='#'>新聞追蹤小幫手</a> — 自動為您產生的專屬報表", "en": "Powered by <a href='#'>News Clipping Tool</a> — automatically generated newsletter"},
    "report_no_news": {"zh": "今天沒有找到符合您關注條件的新聞喔！", "en": "No articles found matching your criteria today!"},
    "report_filename": {"zh": "每日新聞_{t}.html", "en": "Daily_News_{t}.html"},
}

def t(key: str, lang: str = "zh", **kwargs: Any) -> str:
    """Return the translated string for *key* in *lang*."""
    text = _I18N.get(key, {}).get(lang, key)
    if kwargs:
        return text.format(**kwargs)
    return text


@dataclass
class Article:
    """Data class for normalized news items."""
    __slots__ = ["title", "url", "source", "published", "summary", "category", "keyword", "timestamp"]

    title: str
    url: str
    source: str
    published: str
    summary: str
    category: str
    keyword: str
    timestamp: float


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("news_clipping")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_file = os.path.join(BASE_DIR, "newsclipping.log")
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if unwriteable directory
            logger.error("Failed to setup file logger at %s: %s", log_file, e)

    return logger

log = _setup_logger()
