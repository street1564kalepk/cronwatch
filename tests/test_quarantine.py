"""Tests for cronwatch.quarantine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.quarantine import QuarantineEntry, QuarantineStore

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path: Path) -> QuarantineStore:
    return QuarantineStore(tmp_path / "quarantine.json")


def test_load_returns_empty_when_file_missing(store: QuarantineStore) -> None:
    assert store.all_entries() == []


def test_quarantine_creates_active_entry(store: QuarantineStore) -> None:
    entry = store.quarantine("backup", "too many failures", now=_NOW)
    assert entry.job_name == "backup"
    assert entry.reason == "too many failures"
    assert entry.is_active()
    assert entry.quarantined_at == _NOW
    assert entry.released_at is None


def test_is_quarantined_returns_true_for_active(store: QuarantineStore) -> None:
    store.quarantine("sync", "manual", now=_NOW)
    assert store.is_quarantined("sync") is True


def test_is_quarantined_returns_false_for_unknown(store: QuarantineStore) -> None:
    assert store.is_quarantined("unknown_job") is False


def test_release_deactivates_entry(store: QuarantineStore) -> None:
    store.quarantine("cleanup", "flapping", now=_NOW)
    released_at = _NOW + timedelta(hours=2)
    result = store.release("cleanup", now=released_at)
    assert result is True
    assert store.is_quarantined("cleanup") is False
    entry = store.all_entries()[0]
    assert entry.released_at == released_at


def test_release_returns_false_for_unknown_job(store: QuarantineStore) -> None:
    result = store.release("ghost", now=_NOW)
    assert result is False


def test_release_returns_false_when_already_released(store: QuarantineStore) -> None:
    store.quarantine("job", "reason", now=_NOW)
    store.release("job", now=_NOW + timedelta(hours=1))
    result = store.release("job", now=_NOW + timedelta(hours=2))
    assert result is False


def test_active_entries_excludes_released(store: QuarantineStore) -> None:
    store.quarantine("job_a", "r1", now=_NOW)
    store.quarantine("job_b", "r2", now=_NOW)
    store.release("job_a", now=_NOW + timedelta(hours=1))
    active = store.active_entries()
    assert len(active) == 1
    assert active[0].job_name == "job_b"


def test_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    s1 = QuarantineStore(path)
    s1.quarantine("etl", "circuit open", now=_NOW)
    s2 = QuarantineStore(path)
    assert s2.is_quarantined("etl") is True
    assert s2.all_entries()[0].reason == "circuit open"


def test_entry_to_dict_roundtrip() -> None:
    entry = QuarantineEntry(
        job_name="test",
        reason="manual",
        quarantined_at=_NOW,
        released_at=_NOW + timedelta(hours=3),
    )
    restored = QuarantineEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.reason == entry.reason
    assert restored.quarantined_at == entry.quarantined_at
    assert restored.released_at == entry.released_at
