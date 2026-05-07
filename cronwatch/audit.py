"""Audit log for cronwatch — records significant system events to a persistent log file."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

AUDIT_VERSION = 1


@dataclass
class AuditEvent:
    timestamp: str
    event_type: str
    job_name: Optional[str]
    detail: str
    actor: str = "cronwatch"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        return cls(
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            job_name=data.get("job_name"),
            detail=data["detail"],
            actor=data.get("actor", "cronwatch"),
        )


class AuditStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> List[AuditEvent]:
        if not self._path.exists():
            return []
        events: List[AuditEvent] = []
        with self._path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(AuditEvent.from_dict(json.loads(line)))
                except (KeyError, json.JSONDecodeError) as exc:
                    logger.warning("Skipping malformed audit line: %s", exc)
        return events

    def append(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")


def record(
    store: AuditStore,
    event_type: str,
    detail: str,
    job_name: Optional[str] = None,
    actor: str = "cronwatch",
) -> AuditEvent:
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type=event_type,
        job_name=job_name,
        detail=detail,
        actor=actor,
    )
    store.append(event)
    logger.debug("audit: [%s] %s", event_type, detail)
    return event


def filter_events(
    events: List[AuditEvent],
    event_type: Optional[str] = None,
    job_name: Optional[str] = None,
) -> List[AuditEvent]:
    return [
        e for e in events
        if (event_type is None or e.event_type == event_type)
        and (job_name is None or e.job_name == job_name)
    ]
