"""Read / write the YAML configuration file with sensible defaults."""

from __future__ import annotations

import copy
import os
from typing import Any

import yaml

from utils import CONFIG_PATH, log

# ---------------------------------------------------------------------------
# Default configuration (used when keys are missing)
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "schedule": {
        "send_times": ["08:00"],
        "timezone": "Asia/Taipei",
    },
    "keywords": [],
    "categories": ["technology"],
    "sources": {
        "google_news": {"enabled": True, "language": "zh-TW", "region": "TW"},
        "rss_feeds": {"enabled": True, "urls": []},
        "reddit": {"enabled": True, "subreddits": ["technology"]},
    },
    "max_articles_per_source": 10,
    "max_summary_length": 200,
    "output_dir": os.path.join(os.path.expanduser("~"), "Desktop"),
    "autostart": False,
    "language": "zh",
    "date_range": {
        "enabled": False,
        "start": "",
        "end": ""
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, preferring override values."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: str = CONFIG_PATH) -> dict[str, Any]:
    """Load configuration from *path*, filling in defaults for missing keys."""
    if not os.path.exists(path):
        log.warning("Config file not found at %s, creating default config", path)
        save_config(_DEFAULTS, path)
        return copy.deepcopy(_DEFAULTS)

    with open(path, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] | None = yaml.safe_load(fh)

    if not raw:
        raw = {}

    merged = _deep_merge(_DEFAULTS, raw)
    log.info("Configuration loaded from %s", path)
    return merged


def save_config(cfg: dict[str, Any], path: str = CONFIG_PATH) -> None:
    """Persist *cfg* to *path* as YAML."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True) # Ensure dir exists
    
    # Remove old email keys if they still exist in the dict
    if "gmail" in cfg:
        del cfg["gmail"]

    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(
            cfg,
            fh,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    log.info("Configuration saved to %s", path)


def get_defaults() -> dict[str, Any]:
    """Return a deep copy of the built-in defaults."""
    return copy.deepcopy(_DEFAULTS)
