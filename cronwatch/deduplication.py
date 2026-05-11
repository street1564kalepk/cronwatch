"""Deduplication: suppress duplicate alerts for the same job failure within a cooldown window."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)

_SENTINEL = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass
class DedupeEntry:
    job_name: str
    last_alerted: datetime
    alert_type: str  # e.g. "failure" or "overdue"

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_alerted": self.last_alerted.isoformat(),
            "alert_type": self.alert_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DedupeEntry":
        return cls(
            job_name=data["job_name"],
            last_alerted=datetime.fromisoformat(data["last_alerted"]),
            alert_type=data["alert_type"],
        )


class DeduplicationStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: Dict[str, DedupeEntry] = {}
        self._load()

    def _key(self, job_name: str, alert_type: str) -> str:
        return f"{job_name}:{alert_type}"

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            for item in raw:
                entry = DedupeEntry.from_dict(item)
                self._entries[self._key(entry.job_name, entry.alert_type)] = entry
        except Exception:
            log.warning("Failed to load deduplication store from %s", self._path)

    def _save(self) -> None:
        self._path.write_text(json.dumps([e.to_dict() for e in self._entries.values()], indent=2))

    def is_duplicate(
        self,
        job_name: str,
        alert_type: str,
        cooldown: timedelta,
        now: Optional[datetime] = None,
    ) -> bool:
        """Return True if an alert of *alert_type* for *job_name* was already sent within *cooldown*."""
        now = now or datetime.now(timezone.utc)
        key = self._key(job_name, alert_type)
        entry = self._entries.get(key)
        if entry is None:
            return False
        return (now - entry.last_alerted) < cooldown

    def record(
        self,
        job_name: str,
        alert_type: str,
        now: Optional[datetime] = None,
    ) -> None:
        """Record that an alert of *alert_type* was dispatched for *job_name* right now."""
        now = now or datetime.now(timezone.utc)
        key = self._key(job_name, alert_type)
        self._entries[key] = DedupeEntry(job_name=job_name, last_alerted=now, alert_type=alert_type)
        self._save()

    def clear(self, job_name: str, alert_type: str) -> None:
        """Remove the deduplication record for a job/alert pair."""
        key = self._key(job_name, alert_type)
        if key in self._entries:
            del self._entries[key]
            self._save()
