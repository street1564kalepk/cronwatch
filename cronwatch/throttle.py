"""Alert throttling: suppress repeated alerts for the same job within a cooldown window."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_COOLDOWN_MINUTES = 60


@dataclass
class ThrottleEntry:
    job_name: str
    alert_type: str
    last_sent: datetime

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "alert_type": self.alert_type,
            "last_sent": self.last_sent.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "ThrottleEntry":
        return ThrottleEntry(
            job_name=data["job_name"],
            alert_type=data["alert_type"],
            last_sent=datetime.fromisoformat(data["last_sent"]),
        )


@dataclass
class ThrottleStore:
    path: str
    cooldown_minutes: int = _DEFAULT_COOLDOWN_MINUTES
    _entries: Dict[str, ThrottleEntry] = field(default_factory=dict, repr=False)

    def _key(self, job_name: str, alert_type: str) -> str:
        return f"{job_name}::{alert_type}"

    def load(self) -> None:
        if not os.path.exists(self.path):
            self._entries = {}
            return
        with open(self.path, "r") as fh:
            raw = json.load(fh)
        self._entries = {
            k: ThrottleEntry.from_dict(v) for k, v in raw.items()
        }

    def save(self) -> None:
        with open(self.path, "w") as fh:
            json.dump({k: v.to_dict() for k, v in self._entries.items()}, fh, indent=2)

    def is_throttled(self, job_name: str, alert_type: str) -> bool:
        key = self._key(job_name, alert_type)
        entry = self._entries.get(key)
        if entry is None:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.cooldown_minutes)
        return entry.last_sent >= cutoff

    def record(self, job_name: str, alert_type: str) -> None:
        key = self._key(job_name, alert_type)
        self._entries[key] = ThrottleEntry(
            job_name=job_name,
            alert_type=alert_type,
            last_sent=datetime.now(timezone.utc),
        )
        self.save()
        logger.debug("Throttle recorded: %s/%s", job_name, alert_type)

    def clear(self, job_name: Optional[str] = None) -> int:
        if job_name is None:
            count = len(self._entries)
            self._entries.clear()
        else:
            keys = [k for k in self._entries if k.startswith(f"{job_name}::")]
            count = len(keys)
            for k in keys:
                del self._entries[k]
        self.save()
        return count
