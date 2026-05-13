"""Heartbeat tracking: records periodic pings from cron jobs and detects missed heartbeats."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatEntry:
    job_name: str
    last_seen: datetime
    interval_seconds: int
    missed: bool = False

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_seen": self.last_seen.isoformat(),
            "interval_seconds": self.interval_seconds,
            "missed": self.missed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HeartbeatEntry":
        return cls(
            job_name=d["job_name"],
            last_seen=datetime.fromisoformat(d["last_seen"]),
            interval_seconds=d["interval_seconds"],
            missed=d.get("missed", False),
        )


class HeartbeatStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._entries: Dict[str, HeartbeatEntry] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self._path):
            self._entries = {}
            return
        with open(self._path) as f:
            raw = json.load(f)
        self._entries = {k: HeartbeatEntry.from_dict(v) for k, v in raw.items()}

    def save(self) -> None:
        with open(self._path, "w") as f:
            json.dump({k: v.to_dict() for k, v in self._entries.items()}, f, indent=2)

    def ping(self, job_name: str, interval_seconds: int, now: Optional[datetime] = None) -> None:
        """Record a heartbeat ping for a job."""
        ts = now or datetime.now(timezone.utc)
        self._entries[job_name] = HeartbeatEntry(
            job_name=job_name,
            last_seen=ts,
            interval_seconds=interval_seconds,
            missed=False,
        )
        self.save()
        logger.debug("Heartbeat ping recorded for %s", job_name)

    def check(self, now: Optional[datetime] = None) -> List[HeartbeatEntry]:
        """Return entries whose heartbeat interval has been exceeded."""
        ts = now or datetime.now(timezone.utc)
        missed: List[HeartbeatEntry] = []
        for entry in self._entries.values():
            deadline = entry.last_seen + timedelta(seconds=entry.interval_seconds)
            if ts > deadline:
                entry.missed = True
                missed.append(entry)
                logger.warning("Missed heartbeat for job %s (last seen %s)", entry.job_name, entry.last_seen)
        if missed:
            self.save()
        return missed

    def get(self, job_name: str) -> Optional[HeartbeatEntry]:
        return self._entries.get(job_name)

    def all_entries(self) -> List[HeartbeatEntry]:
        return list(self._entries.values())

    def remove(self, job_name: str) -> bool:
        if job_name in self._entries:
            del self._entries[job_name]
            self.save()
            return True
        return False
