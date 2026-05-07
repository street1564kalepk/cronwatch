"""Tests for cronwatch.throttle."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.throttle import ThrottleEntry, ThrottleStore


@pytest.fixture
def store(tmp_path):
    s = ThrottleStore(path=str(tmp_path / "throttle.json"), cooldown_minutes=60)
    s.load()
    return s


def test_load_returns_empty_when_file_missing(store):
    assert store._entries == {}


def test_is_throttled_returns_false_for_unknown_job(store):
    assert store.is_throttled("backup", "failure") is False


def test_record_marks_job_as_throttled(store):
    store.record("backup", "failure")
    assert store.is_throttled("backup", "failure") is True


def test_throttle_expires_after_cooldown(store):
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=61)
    key = "backup::failure"
    store._entries[key] = ThrottleEntry(
        job_name="backup",
        alert_type="failure",
        last_sent=expired_time,
    )
    assert store.is_throttled("backup", "failure") is False


def test_record_persists_to_disk(store):
    store.record("nightly", "overdue")
    assert os.path.exists(store.path)
    with open(store.path) as fh:
        data = json.load(fh)
    assert "nightly::overdue" in data


def test_clear_all_removes_all_entries(store):
    store.record("job_a", "failure")
    store.record("job_b", "overdue")
    count = store.clear()
    assert count == 2
    assert store._entries == {}


def test_clear_by_job_removes_only_that_job(store):
    store.record("job_a", "failure")
    store.record("job_a", "overdue")
    store.record("job_b", "failure")
    count = store.clear(job_name="job_a")
    assert count == 2
    assert store.is_throttled("job_b", "failure") is True
    assert store.is_throttled("job_a", "failure") is False


def test_roundtrip_preserves_entry(store):
    store.record("sync", "failure")
    store2 = ThrottleStore(path=store.path, cooldown_minutes=60)
    store2.load()
    assert store2.is_throttled("sync", "failure") is True


def test_different_alert_types_tracked_independently(store):
    store.record("myjob", "failure")
    assert store.is_throttled("myjob", "failure") is True
    assert store.is_throttled("myjob", "overdue") is False
