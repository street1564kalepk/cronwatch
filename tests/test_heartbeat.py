"""Tests for cronwatch.heartbeat."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.heartbeat import HeartbeatEntry, HeartbeatStore


@pytest.fixture
def store(tmp_path):
    return HeartbeatStore(str(tmp_path / "heartbeat.json"))


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_load_returns_empty_when_file_missing(store):
    assert store.all_entries() == []


def test_ping_creates_entry(store):
    store.ping("backup", interval_seconds=3600, now=NOW)
    entry = store.get("backup")
    assert entry is not None
    assert entry.job_name == "backup"
    assert entry.last_seen == NOW
    assert entry.interval_seconds == 3600
    assert entry.missed is False


def test_ping_persists_to_disk(store, tmp_path):
    store.ping("backup", interval_seconds=3600, now=NOW)
    store2 = HeartbeatStore(str(tmp_path / "heartbeat.json"))
    entry = store2.get("backup")
    assert entry is not None
    assert entry.last_seen == NOW


def test_check_returns_empty_when_within_interval(store):
    store.ping("backup", interval_seconds=3600, now=NOW)
    missed = store.check(now=NOW + timedelta(seconds=1800))
    assert missed == []


def test_check_returns_entry_when_overdue(store):
    store.ping("backup", interval_seconds=3600, now=NOW)
    missed = store.check(now=NOW + timedelta(seconds=3601))
    assert len(missed) == 1
    assert missed[0].job_name == "backup"
    assert missed[0].missed is True


def test_check_marks_missed_on_disk(store, tmp_path):
    store.ping("backup", interval_seconds=3600, now=NOW)
    store.check(now=NOW + timedelta(seconds=7200))
    store2 = HeartbeatStore(str(tmp_path / "heartbeat.json"))
    assert store2.get("backup").missed is True


def test_check_only_flags_overdue_jobs(store):
    store.ping("fast_job", interval_seconds=60, now=NOW)
    store.ping("slow_job", interval_seconds=86400, now=NOW)
    missed = store.check(now=NOW + timedelta(seconds=120))
    assert len(missed) == 1
    assert missed[0].job_name == "fast_job"


def test_remove_deletes_entry(store):
    store.ping("backup", interval_seconds=3600, now=NOW)
    result = store.remove("backup")
    assert result is True
    assert store.get("backup") is None


def test_remove_unknown_returns_false(store):
    assert store.remove("nonexistent") is False


def test_all_entries_returns_all(store):
    store.ping("job_a", interval_seconds=60, now=NOW)
    store.ping("job_b", interval_seconds=120, now=NOW)
    names = {e.job_name for e in store.all_entries()}
    assert names == {"job_a", "job_b"}


def test_heartbeat_entry_roundtrip():
    entry = HeartbeatEntry(job_name="test", last_seen=NOW, interval_seconds=300, missed=True)
    restored = HeartbeatEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.last_seen == entry.last_seen
    assert restored.interval_seconds == entry.interval_seconds
    assert restored.missed == entry.missed
