"""Alert escalation: track repeated failures and escalate after a threshold."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 3


@dataclass
class EscalationState:
    job_name: str
    consecutive_failures: int = 0
    escalated: bool = False

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "consecutive_failures": self.consecutive_failures,
            "escalated": self.escalated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EscalationState":
        return cls(
            job_name=data["job_name"],
            consecutive_failures=data.get("consecutive_failures", 0),
            escalated=data.get("escalated", False),
        )


class EscalationStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._states: Dict[str, EscalationState] = {}
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._states = {}
            return
        try:
            raw = json.loads(self._path.read_text())
            self._states = {
                k: EscalationState.from_dict(v) for k, v in raw.items()
            }
        except Exception:
            logger.warning("Failed to load escalation state from %s", self._path)
            self._states = {}

    def save(self) -> None:
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._states.items()}, indent=2)
        )

    def get(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState(job_name=job_name)
        return self._states[job_name]

    def record_failure(self, job_name: str, threshold: int = _DEFAULT_THRESHOLD) -> bool:
        """Record a failure. Returns True if escalation threshold was just crossed."""
        state = self.get(job_name)
        state.consecutive_failures += 1
        newly_escalated = False
        if not state.escalated and state.consecutive_failures >= threshold:
            state.escalated = True
            newly_escalated = True
            logger.warning(
                "Job '%s' escalated after %d consecutive failures.",
                job_name,
                state.consecutive_failures,
            )
        self.save()
        return newly_escalated

    def record_success(self, job_name: str) -> None:
        """Reset failure count on success."""
        state = self.get(job_name)
        state.consecutive_failures = 0
        state.escalated = False
        self.save()

    def is_escalated(self, job_name: str) -> bool:
        return self.get(job_name).escalated

    def consecutive_failures(self, job_name: str) -> int:
        return self.get(job_name).consecutive_failures
