"""Quarantine store: track jobs that have been quarantined due to repeated failures."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class QuarantineEntry:
    job_name: str
    reason: str
    quarantined_at: datetime
    released_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.released_at is None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "reason": self.reason,
            "quarantined_at": self.quarantined_at.strftime(_DATE_FMT),
            "released_at": self.released_at.strftime(_DATE_FMT) if self.released_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuarantineEntry":
        return cls(
            job_name=d["job_name"],
            reason=d["reason"],
            quarantined_at=datetime.strptime(d["quarantined_at"], _DATE_FMT).replace(tzinfo=timezone.utc),
            released_at=(
                datetime.strptime(d["released_at"], _DATE_FMT).replace(tzinfo=timezone.utc)
                if d.get("released_at")
                else None
            ),
        )


class QuarantineStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: Dict[str, QuarantineEntry] = {}
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._entries = {}
            return
        try:
            raw = json.loads(self._path.read_text())
            self._entries = {k: QuarantineEntry.from_dict(v) for k, v in raw.items()}
        except Exception:
            log.warning("Failed to load quarantine store from %s", self._path)
            self._entries = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2))

    def quarantine(self, job_name: str, reason: str, now: Optional[datetime] = None) -> QuarantineEntry:
        now = now or datetime.now(timezone.utc)
        entry = QuarantineEntry(job_name=job_name, reason=reason, quarantined_at=now)
        self._entries[job_name] = entry
        self._save()
        log.info("Job %r quarantined: %s", job_name, reason)
        return entry

    def release(self, job_name: str, now: Optional[datetime] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None or not entry.is_active():
            return False
        entry.released_at = now or datetime.now(timezone.utc)
        self._save()
        log.info("Job %r released from quarantine", job_name)
        return True

    def is_quarantined(self, job_name: str) -> bool:
        entry = self._entries.get(job_name)
        return entry is not None and entry.is_active()

    def active_entries(self) -> List[QuarantineEntry]:
        return [e for e in self._entries.values() if e.is_active()]

    def all_entries(self) -> List[QuarantineEntry]:
        return list(self._entries.values())
