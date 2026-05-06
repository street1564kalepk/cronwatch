"""Silence (suppress) alerts for specific jobs during maintenance windows."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SilenceRule:
    job_name: str
    reason: str
    start: datetime
    end: datetime
    created_by: str = "unknown"

    def is_active(self, at: Optional[datetime] = None) -> bool:
        now = at or datetime.now(timezone.utc)
        return self.start <= now <= self.end


@dataclass
class SilenceStore:
    path: Path
    _rules: List[SilenceRule] = field(default_factory=list)

    def load(self) -> None:
        if not self.path.exists():
            self._rules = []
            return
        with self.path.open() as fh:
            raw = json.load(fh)
        self._rules = [
            SilenceRule(
                job_name=r["job_name"],
                reason=r["reason"],
                start=datetime.fromisoformat(r["start"]),
                end=datetime.fromisoformat(r["end"]),
                created_by=r.get("created_by", "unknown"),
            )
            for r in raw
        ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as fh:
            json.dump(
                [
                    {
                        "job_name": r.job_name,
                        "reason": r.reason,
                        "start": r.start.isoformat(),
                        "end": r.end.isoformat(),
                        "created_by": r.created_by,
                    }
                    for r in self._rules
                ],
                fh,
                indent=2,
            )

    def add(self, rule: SilenceRule) -> None:
        self._rules.append(rule)
        self.save()
        logger.info("Silenced %s until %s (%s)", rule.job_name, rule.end, rule.reason)

    def remove_expired(self) -> int:
        before = len(self._rules)
        now = datetime.now(timezone.utc)
        self._rules = [r for r in self._rules if r.end > now]
        removed = before - len(self._rules)
        if removed:
            self.save()
        return removed

    def is_silenced(self, job_name: str, at: Optional[datetime] = None) -> bool:
        return any(r.job_name == job_name and r.is_active(at) for r in self._rules)

    def active_rules(self) -> List[SilenceRule]:
        return [r for r in self._rules if r.is_active()]

    def all_rules(self) -> List[SilenceRule]:
        return list(self._rules)
