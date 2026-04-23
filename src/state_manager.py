"""Persistent deduplication for processed RSS entries."""

import json
import os
from datetime import datetime, timedelta

from src.config import Config

_RETENTION_DAYS = 30


class StateManager:
    """Tracks which RSS entries have already been processed to avoid duplicates."""

    def __init__(self) -> None:
        self._path = Config.STATE_FILE
        self._data: dict[str, str] = {}  # entry_id -> process_date (ISO)
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_processed(self, entry_id: str) -> bool:
        """Return True if *entry_id* has been handled before."""
        return entry_id in self._data

    def mark_processed(self, entry_id: str) -> None:
        """Record *entry_id* as processed today."""
        self._data[entry_id] = datetime.now().isoformat()

    def mark_batch(self, entry_ids: list[str]) -> None:
        """Record multiple entry IDs at once."""
        for eid in entry_ids:
            self.mark_processed(eid)

    def save(self) -> None:
        """Write state to disk and purge stale entries."""
        self._purge_stale()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            self._data = {}
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _purge_stale(self) -> None:
        cutoff = datetime.now() - timedelta(days=_RETENTION_DAYS)
        stale = [
            eid
            for eid, date_str in self._data.items()
            if _parse_iso(date_str) is None or _parse_iso(date_str) < cutoff
        ]
        for eid in stale:
            del self._data[eid]


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
