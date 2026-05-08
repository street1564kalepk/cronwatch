"""Tests for cronwatch.escalation."""

from __future__ import annotations

import pytest
from pathlib import Path

from cronwatch.escalation import EscalationState, EscalationStore


@pytest.fixture
def store(tmp_path: Path) -> EscalationStore:
    return EscalationStore(tmp_path / "escalation.json")


def test_load_returns_empty_when_file_missing(store: EscalationStore) -> None:
    assert store._states == {}


def test_consecutive_failures_starts_at_zero(store: EscalationStore) -> None:
    assert store.consecutive_failures("backup") == 0


def test_record_failure_increments_count(store: EscalationStore) -> None:
    store.record_failure("backup", threshold=5)
    assert store.consecutive_failures("backup") == 1


def test_record_failure_returns_false_below_threshold(store: EscalationStore) -> None:
    result = store.record_failure("backup", threshold=3)
    assert result is False
    assert not store.is_escalated("backup")


def test_record_failure_returns_true_at_threshold(store: EscalationStore) -> None:
    for _ in range(2):
        store.record_failure("backup", threshold=3)
    result = store.record_failure("backup", threshold=3)
    assert result is True
    assert store.is_escalated("backup")


def test_record_failure_only_escalates_once(store: EscalationStore) -> None:
    for _ in range(3):
        store.record_failure("backup", threshold=3)
    result = store.record_failure("backup", threshold=3)
    assert result is False  # already escalated, not newly
    assert store.consecutive_failures("backup") == 4


def test_record_success_resets_state(store: EscalationStore) -> None:
    for _ in range(3):
        store.record_failure("backup", threshold=3)
    assert store.is_escalated("backup")
    store.record_success("backup")
    assert not store.is_escalated("backup")
    assert store.consecutive_failures("backup") == 0


def test_state_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "escalation.json"
    s1 = EscalationStore(path)
    s1.record_failure("nightly", threshold=10)
    s1.record_failure("nightly", threshold=10)

    s2 = EscalationStore(path)
    assert s2.consecutive_failures("nightly") == 2


def test_escalation_state_roundtrip() -> None:
    original = EscalationState(job_name="deploy", consecutive_failures=4, escalated=True)
    restored = EscalationState.from_dict(original.to_dict())
    assert restored.job_name == original.job_name
    assert restored.consecutive_failures == original.consecutive_failures
    assert restored.escalated == original.escalated


def test_independent_jobs_do_not_interfere(store: EscalationStore) -> None:
    for _ in range(3):
        store.record_failure("job_a", threshold=3)
    assert store.is_escalated("job_a")
    assert not store.is_escalated("job_b")
