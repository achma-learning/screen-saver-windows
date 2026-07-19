"""
config_manager.py
------------------
Centralized configuration storage for the HTML Screensaver application.

Settings are persisted as JSON under:
    %APPDATA%\\HtmlScreensaver\\config.json

This keeps the app's data out of Program Files (which may be read-only for
the current user) and follows standard Windows conventions for per-user
application data.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


APP_NAME = "HtmlScreensaver"


def _appdata_dir() -> Path:
    """Return (and create if necessary) the per-user app-data directory."""
    base = os.environ.get("APPDATA")
    if not base:
        # Fallback for non-Windows dev/test environments.
        base = str(Path.home() / ".config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


CONFIG_PATH = _appdata_dir() / "config.json"
LOG_PATH = _appdata_dir() / "screensaver.log"


@dataclass
class AppConfig:
    content_source: str = ""         # local .html path OR http(s):// URL
    timeout_minutes: int = 10        # inactivity minutes before screensaver launches
    enabled: bool = True             # whether the monitor loop is active
    autostart: bool = False          # whether the app launches at Windows logon
    first_run_complete: bool = False # whether the setup wizard has been completed
    lock_on_wake: bool = False       # optional: lock workstation after screensaver closes
    skip_if_fullscreen_app: bool = True  # don't interrupt games/movies/presentations
    dev_mode: bool = False           # disable cache + auto-reload on file change, for HTML dev

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AppConfig":
        d = dict(d)
        if "html_path" in d and "content_source" not in d:
            # Migrate configs written by earlier versions of this app.
            d["content_source"] = d.pop("html_path")
        defaults = AppConfig()
        merged = {**defaults.to_dict(), **{k: v for k, v in d.items() if k in defaults.to_dict()}}
        return AppConfig(**merged)


class ConfigManager:
    """Thread-unsafe (Qt main-thread only) simple JSON-backed config store."""

    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self._config = self._load()

    def _load(self) -> AppConfig:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return AppConfig.from_dict(raw)
            except (json.JSONDecodeError, OSError):
                # Corrupt config -- fall back to defaults rather than crashing.
                return AppConfig()
        return AppConfig()

    def save(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._config.to_dict(), f, indent=2)
        # Atomic replace avoids a corrupted config if the process is killed mid-write.
        os.replace(tmp_path, self.path)

    @property
    def config(self) -> AppConfig:
        return self._config

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
            else:
                raise AttributeError(f"Unknown config field: {k}")
        self.save()


def log(message: str) -> None:
    """Very small append-only logger; avoids pulling in logging config overhead."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except OSError:
        pass
