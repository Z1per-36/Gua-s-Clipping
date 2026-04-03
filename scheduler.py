"""APScheduler-based job scheduler for timed news delivery."""

from __future__ import annotations

import gc
import os
import webbrowser
from datetime import datetime
from typing import Any
from urllib.request import pathname2url

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from plyer import notification

from config_manager import load_config
from utils import log


def _run_pipeline() -> None:
    """Execute the full scrape -> compile -> popup pipeline."""
    log.info("=== Scheduled popup pipeline triggered ===")
    cfg = load_config()  # reload config each run so edits take effect

    lang = cfg.get("language", "zh")
    from utils import t
    
    # Notify user that fetching has started since it can take time
    try:
        notification.notify(
            title=t("notif_title", lang),
            message=t("notif_fetching", lang),
            app_name="News Clipping Tool",
            timeout=3
        )
    except Exception as e:
        log.warning("Initial notification failed: %s", e)

    # --- Scrape ---------------------------------------------------------------
    from scrapers import run_all_scrapers
    articles = run_all_scrapers(cfg)

    # --- Compile --------------------------------------------------------------
    from news_compiler import compile_articles
    html_body, total = compile_articles(articles, lang=lang)

    if total == 0:
        log.info("No articles found — skipping popup")
        gc.collect()
        return

    # --- Determine Output Path ------------------------------------------------
    from utils import t
    output_dir = cfg.get("output_dir")
    if not output_dir or not os.path.exists(output_dir):
        output_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = t("report_filename", lang, t=timestamp)
    filepath = os.path.join(output_dir, filename)

    # --- Save & Show ----------------------------------------------------------
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_body)
        log.info("Saved news report to %s", filepath)
    except Exception as e:
        log.error("Failed to write html file: %s", e)
        gc.collect()
        return

    # Try Windows Notification
    try:
        notification.notify(
            title=t("notif_title", lang),
            message=t("notif_msg", lang, t=total),
            app_name="News Clipping Tool",
            timeout=10
        )
    except Exception as e:
        log.warning("System notification failed: %s", e)

    # Open standard default browser
    file_uri = "file:" + pathname2url(os.path.abspath(filepath))
    webbrowser.open(file_uri)

    # Free large string
    del html_body
    gc.collect()
    log.info("=== Popup Pipeline complete ===")


class NewsScheduler:
    """Manages APScheduler jobs based on config send_times."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._job_ids: list[str] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def start(self, cfg: dict[str, Any]) -> None:
        """Start the scheduler and add jobs based on *cfg*."""
        self._rebuild_jobs(cfg)
        if not self._scheduler.running:
            self._scheduler.start()
        log.info("Scheduler started")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")

    def reload(self, cfg: dict[str, Any]) -> None:
        """Remove existing jobs and rebuild from *cfg*."""
        self._rebuild_jobs(cfg)
        log.info("Scheduler jobs reloaded")

    def trigger_now(self) -> None:
        """Immediately run the pipeline (outside the schedule)."""
        log.info("Manual trigger requested")
        _run_pipeline()

    @property
    def next_run(self) -> str | None:
        """Return a human-readable string of the next scheduled run."""
        jobs = self._scheduler.get_jobs()
        if not jobs:
            return None
        next_times = [j.next_run_time for j in jobs if j.next_run_time]
        if not next_times:
            return None
        earliest = min(next_times)
        return earliest.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_jobs(self, cfg: dict[str, Any]) -> None:
        """Clear and recreate cron jobs from config send_times."""
        for jid in self._job_ids:
            try:
                self._scheduler.remove_job(jid)
            except Exception:
                pass
        self._job_ids.clear()

        schedule_cfg = cfg.get("schedule", {})
        tz = schedule_cfg.get("timezone", "Asia/Taipei")
        send_times: list[str] = schedule_cfg.get("send_times", [])

        if not send_times:
            return

        for idx, time_str in enumerate(send_times):
            time_str = time_str.strip()
            if not time_str:
                continue
            try:
                parts = time_str.split(":")
                hour, minute = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                log.warning("Invalid send_time format: '%s', skipping", time_str)
                continue

            job_id = f"news_send_{idx}"
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self._scheduler.add_job(
                _run_pipeline,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
            )
            self._job_ids.append(job_id)
            log.info("Scheduled job '%s' at %02d:%02d (%s)", job_id, hour, minute, tz)
