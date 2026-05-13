"""Circuit breaker for cron jobs — pause alerting/execution after repeated failures."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)

STATE_CLOSED = "closed"       # normal operation
STATE_OPEN = "open"           # tripped; job is suppressed
STATE_HALF_OPEN = "half_open" # testing recovery


@dataclass
class BreakerState:
    job_name: str
    state: str = STATE_CLOSED
    failure_count: int = 0
    opened_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "state": self.state,
            "failure_count": self.failure_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
        }

    @staticmethod
    def from_dict(d: dict) -> "BreakerState":
        return BreakerState(
            job_name=d["job_name"],
            state=d["state"],
            failure_count=d["failure_count"],
            opened_at=datetime.fromisoformat(d["opened_at"]) if d.get("opened_at") else None,
            last_checked=datetime.fromisoformat(d["last_checked"]) if d.get("last_checked") else None,
        )


class CircuitBreakerStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: Dict[str, BreakerState] = {}
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._data = {}
            return
        raw = json.loads(self._path.read_text())
        self._data = {k: BreakerState.from_dict(v) for k, v in raw.items()}

    def save(self) -> None:
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._data.items()}, indent=2))

    def get(self, job_name: str) -> BreakerState:
        return self._data.get(job_name, BreakerState(job_name=job_name))

    def put(self, state: BreakerState) -> None:
        self._data[state.job_name] = state
        self.save()

    def all(self) -> list[BreakerState]:
        return list(self._data.values())


def record_failure(store: CircuitBreakerStore, job_name: str, threshold: int = 3) -> BreakerState:
    """Increment failure count; open the breaker when threshold is reached."""
    state = store.get(job_name)
    state.failure_count += 1
    state.last_checked = datetime.now(timezone.utc)
    if state.failure_count >= threshold and state.state == STATE_CLOSED:
        state.state = STATE_OPEN
        state.opened_at = datetime.now(timezone.utc)
        log.warning("Circuit breaker OPENED for job '%s' after %d failures.", job_name, state.failure_count)
    store.put(state)
    return state


def record_success(store: CircuitBreakerStore, job_name: str) -> BreakerState:
    """Reset the breaker on a successful run."""
    state = store.get(job_name)
    if state.state in (STATE_OPEN, STATE_HALF_OPEN):
        log.info("Circuit breaker CLOSED for job '%s' after successful run.", job_name)
    state.state = STATE_CLOSED
    state.failure_count = 0
    state.opened_at = None
    state.last_checked = datetime.now(timezone.utc)
    store.put(state)
    return state


def is_open(state: BreakerState, recovery_minutes: int = 30) -> bool:
    """Return True if the breaker is open (and recovery window has not elapsed)."""
    if state.state == STATE_CLOSED:
        return False
    if state.state == STATE_HALF_OPEN:
        return False
    if state.opened_at is None:
        return False
    elapsed = datetime.now(timezone.utc) - state.opened_at
    if elapsed >= timedelta(minutes=recovery_minutes):
        return False  # allow half-open probe
    return True


def maybe_half_open(store: CircuitBreakerStore, job_name: str, recovery_minutes: int = 30) -> BreakerState:
    """Transition OPEN -> HALF_OPEN once the recovery window elapses."""
    state = store.get(job_name)
    if state.state != STATE_OPEN or state.opened_at is None:
        return state
    elapsed = datetime.now(timezone.utc) - state.opened_at
    if elapsed >= timedelta(minutes=recovery_minutes):
        state.state = STATE_HALF_OPEN
        log.info("Circuit breaker HALF-OPEN for job '%s'; probing recovery.", job_name)
        store.put(state)
    return state
