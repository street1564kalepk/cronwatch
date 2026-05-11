"""Tests for cronwatch.deduplication."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.deduplication import DedupeEntry, DeduplicationStore

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
_COOLDOWN = timedelta(minutes=30)


@pytest.fixture
def store(tmp_path: Path) -> DeduplicationStore:
    return DeduplicationStore(tmp_path / "dedupe.json")


def test_load_returns_empty_when_file_missing(store: DeduplicationStore) -> None:
    assert not store._entries


def test_is_duplicate_returns_false_for_unknown_job(store: DeduplicationStore) -> None:
    assert store.is_duplicate("backup", "failure", _COOLDOWN, now=_NOW) is False


def test_record_marks_job_as_duplicate(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    assert store.is_duplicate("backup", "failure", _COOLDOWN, now=_NOW) is True


def test_duplicate_expires_after_cooldown(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    future = _NOW + _COOLDOWN + timedelta(seconds=1)
    assert store.is_duplicate("backup", "failure", _COOLDOWN, now=future) is False


def test_duplicate_still_active_just_before_expiry(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    almost = _NOW + _COOLDOWN - timedelta(seconds=1)
    assert store.is_duplicate("backup", "failure", _COOLDOWN, now=almost) is True


def test_different_alert_types_are_independent(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    assert store.is_duplicate("backup", "overdue", _COOLDOWN, now=_NOW) is False


def test_different_jobs_are_independent(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    assert store.is_duplicate("sync", "failure", _COOLDOWN, now=_NOW) is False


def test_clear_removes_record(store: DeduplicationStore) -> None:
    store.record("backup", "failure", now=_NOW)
    store.clear("backup", "failure")
    assert store.is_duplicate("backup", "failure", _COOLDOWN, now=_NOW) is False


def test_clear_nonexistent_is_noop(store: DeduplicationStore) -> None:
    store.clear("ghost", "failure")  # should not raise


def test_persists_across_reload(tmp_path: Path) -> None:
    path = tmp_path / "dedupe.json"
    s1 = DeduplicationStore(path)
    s1.record("backup", "failure", now=_NOW)

    s2 = DeduplicationStore(path)
    assert s2.is_duplicate("backup", "failure", _COOLDOWN, now=_NOW) is True


def test_dedupe_entry_roundtrip() -> None:
    entry = DedupeEntry(job_name="nightly", last_alerted=_NOW, alert_type="overdue")
    restored = DedupeEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.last_alerted == entry.last_alerted
    assert restored.alert_type == entry.alert_type
