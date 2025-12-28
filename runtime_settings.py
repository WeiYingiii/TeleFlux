# -*- coding: utf-8 -*-
"""Runtime settings persistence for TeleFlux.

This module stores a small JSON file under the cache directory so that
configuration changed via Telegram commands survives container restarts.

Settings kept here are intentionally minimal:
- proxy_url: A proxy URL string (e.g. socks5://user:pass@host:1080)
- max_concurrent_downloads: int
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RuntimeSettings:
    proxy_url: Optional[str] = None
    max_concurrent_downloads: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proxy_url": self.proxy_url,
            "max_concurrent_downloads": self.max_concurrent_downloads,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RuntimeSettings":
        rs = RuntimeSettings()
        if isinstance(d.get("proxy_url"), str):
            rs.proxy_url = d.get("proxy_url")
        mcd = d.get("max_concurrent_downloads")
        if isinstance(mcd, int):
            rs.max_concurrent_downloads = mcd
        elif isinstance(mcd, str) and mcd.isdigit():
            rs.max_concurrent_downloads = int(mcd)
        return rs


def default_settings_path(cache_path: str) -> Path:
    # Make sure cache directory exists.
    try:
        os.makedirs(cache_path, exist_ok=True)
    except Exception:
        pass
    return Path(cache_path) / "teleflux_settings.json"


def load_settings(path: Path) -> RuntimeSettings:
    try:
        if not path.exists():
            return RuntimeSettings()
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return RuntimeSettings()
        return RuntimeSettings.from_dict(data)
    except Exception as e:
        logger.warning("Failed to load settings: %s (%s)", path, e)
        return RuntimeSettings()


def save_settings(path: Path, settings: RuntimeSettings) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
    except Exception as e:
        logger.warning("Failed to save settings: %s (%s)", path, e)
