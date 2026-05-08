"""Rate limiting for alert dispatches — prevents alert storms."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class RateLimitEntry:
    job_name: str
    alert_type: str
    count: int
    window_start: datetime
    last_sent: datetime

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "alert_type": self.alert_type,
            "count": self.count,
            "window_start": self.window_start.isoformat(),
            "last_sent": self.last_sent.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RateLimitEntry":
        return cls(
            job_name=d["job_name"],
            alert_type=d["alert_type"],
            count=d["count"],
            window_start=datetime.fromisoformat(d["window_start"]),
            last_sent=datetime.fromisoformat(d["last_sent"]),
        )


class RateLimitStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._entries: Dict[str, RateLimitEntry] = {}
        self._load()

    def _key(self, job_name: str, alert_type: str) -> str:
        return f"{job_name}:{alert_type}"

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as fh:
            data = json.load(fh)
        self._entries = {
            k: RateLimitEntry.from_dict(v) for k, v in data.items()
        }

    def _save(self) -> None:
        with open(self._path, "w") as fh:
            json.dump({k: v.to_dict() for k, v in self._entries.items()}, fh, indent=2)

    def is_allowed(
        self,
        job_name: str,
        alert_type: str,
        max_count: int,
        window_seconds: int,
        now: Optional[datetime] = None,
    ) -> bool:
        """Return True if an alert may be sent; False if rate-limited."""
        now = now or datetime.now(timezone.utc)
        key = self._key(job_name, alert_type)
        entry = self._entries.get(key)

        if entry is None:
            self._entries[key] = RateLimitEntry(
                job_name=job_name,
                alert_type=alert_type,
                count=1,
                window_start=now,
                last_sent=now,
            )
            self._save()
            return True

        elapsed = (now - entry.window_start).total_seconds()
        if elapsed >= window_seconds:
            entry.count = 1
            entry.window_start = now
            entry.last_sent = now
            self._save()
            return True

        if entry.count < max_count:
            entry.count += 1
            entry.last_sent = now
            self._save()
            return True

        log.debug(
            "Rate limit hit for %s/%s (%d/%d in window)",
            job_name, alert_type, entry.count, max_count,
        )
        return False

    def reset(self, job_name: str, alert_type: str) -> None:
        key = self._key(job_name, alert_type)
        self._entries.pop(key, None)
        self._save()

    def all_entries(self) -> list:
        return list(self._entries.values())
