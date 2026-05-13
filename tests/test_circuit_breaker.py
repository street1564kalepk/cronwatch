"""Tests for cronwatch.circuit_breaker."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.circuit_breaker import (
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    BreakerState,
    CircuitBreakerStore,
    is_open,
    maybe_half_open,
    record_failure,
    record_success,
)


@pytest.fixture
def store(tmp_path: Path) -> CircuitBreakerStore:
    return CircuitBreakerStore(tmp_path / "breakers.json")


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    s = CircuitBreakerStore(tmp_path / "missing.json")
    assert s.all() == []


def test_record_failure_increments_count(store: CircuitBreakerStore) -> None:
    state = record_failure(store, "backup", threshold=3)
    assert state.failure_count == 1
    assert state.state == STATE_CLOSED


def test_record_failure_opens_at_threshold(store: CircuitBreakerStore) -> None:
    for _ in range(3):
        state = record_failure(store, "backup", threshold=3)
    assert state.state == STATE_OPEN
    assert state.opened_at is not None


def test_record_failure_does_not_reopen_already_open(store: CircuitBreakerStore) -> None:
    for _ in range(5):
        state = record_failure(store, "backup", threshold=3)
    assert state.state == STATE_OPEN  # stays OPEN, not re-opened


def test_record_success_resets_state(store: CircuitBreakerStore) -> None:
    record_failure(store, "backup", threshold=3)
    record_failure(store, "backup", threshold=3)
    state = record_success(store, "backup")
    assert state.state == STATE_CLOSED
    assert state.failure_count == 0
    assert state.opened_at is None


def test_is_open_returns_false_for_closed(store: CircuitBreakerStore) -> None:
    state = store.get("backup")
    assert not is_open(state)


def test_is_open_returns_true_within_recovery_window() -> None:
    state = BreakerState(
        job_name="backup",
        state=STATE_OPEN,
        failure_count=3,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    assert is_open(state, recovery_minutes=30)


def test_is_open_returns_false_after_recovery_window() -> None:
    state = BreakerState(
        job_name="backup",
        state=STATE_OPEN,
        failure_count=3,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=60),
    )
    assert not is_open(state, recovery_minutes=30)


def test_maybe_half_open_transitions_after_window(store: CircuitBreakerStore) -> None:
    s = BreakerState(
        job_name="sync",
        state=STATE_OPEN,
        failure_count=4,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=45),
    )
    store.put(s)
    result = maybe_half_open(store, "sync", recovery_minutes=30)
    assert result.state == STATE_HALF_OPEN


def test_maybe_half_open_no_transition_within_window(store: CircuitBreakerStore) -> None:
    s = BreakerState(
        job_name="sync",
        state=STATE_OPEN,
        failure_count=4,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    store.put(s)
    result = maybe_half_open(store, "sync", recovery_minutes=30)
    assert result.state == STATE_OPEN


def test_persistence_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "breakers.json"
    s1 = CircuitBreakerStore(path)
    record_failure(s1, "etl", threshold=2)
    record_failure(s1, "etl", threshold=2)

    s2 = CircuitBreakerStore(path)
    state = s2.get("etl")
    assert state.state == STATE_OPEN
    assert state.failure_count == 2
