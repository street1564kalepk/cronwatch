"""Time window filtering: restrict alert delivery or checks to defined time ranges."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class TimeWindow:
    """A named time window with optional day-of-week restriction."""

    name: str
    start: time  # inclusive
    end: time    # exclusive
    days: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon … 6=Sun

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if *at* (default: now UTC) falls within this window."""
        at = at or datetime.utcnow()
        if at.weekday() not in self.days:
            return False
        current = at.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current < self.end
        # Overnight window e.g. 22:00 – 06:00
        return current >= self.start or current < self.end

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "days": self.days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeWindow":
        return cls(
            name=data["name"],
            start=time.fromisoformat(data["start"]),
            end=time.fromisoformat(data["end"]),
            days=data.get("days", list(range(7))),
        )


class TimeWindowStore:
    """Persist time windows as JSON."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._windows: List[TimeWindow] = []
        self.load()

    def load(self) -> None:
        if not os.path.exists(self._path):
            self._windows = []
            return
        with open(self._path) as fh:
            raw = json.load(fh)
        self._windows = [TimeWindow.from_dict(d) for d in raw]

    def save(self) -> None:
        with open(self._path, "w") as fh:
            json.dump([w.to_dict() for w in self._windows], fh, indent=2)

    def add(self, window: TimeWindow) -> None:
        self._windows = [w for w in self._windows if w.name != window.name]
        self._windows.append(window)
        self.save()

    def remove(self, name: str) -> bool:
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.name != name]
        if len(self._windows) < before:
            self.save()
            return True
        return False

    def all(self) -> List[TimeWindow]:
        return list(self._windows)

    def get(self, name: str) -> Optional[TimeWindow]:
        return next((w for w in self._windows if w.name == name), None)

    def any_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if at least one window is currently active."""
        return any(w.is_active(at) for w in self._windows)
