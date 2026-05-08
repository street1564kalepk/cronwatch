"""Tests for cronwatch.ratelimit."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.ratelimit import RateLimitEntry, RateLimitStore


@pytest.fixture
def store(tmp_path):
    return RateLimitStore(str(tmp_path / "rl.json"))


def _now():
    return datetime.now(timezone.utc)


def test_load_returns_empty_when_file_missing(store):
    assert store.all_entries() == []


def test_first_call_is_always_allowed(store):
    assert store.is_allowed("backup", "failure", max_count=3, window_seconds=60) is True


def test_within_limit_is_allowed(store):
    now = _now()
    for _ in range(3):
        result = store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)
        assert result is True


def test_exceeding_limit_is_blocked(store):
    now = _now()
    for _ in range(3):
        store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)
    blocked = store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)
    assert blocked is False


def test_window_expiry_resets_counter(store):
    now = _now()
    for _ in range(3):
        store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)

    later = now + timedelta(seconds=61)
    allowed = store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=later)
    assert allowed is True

    entry = next(e for e in store.all_entries() if e.job_name == "backup")
    assert entry.count == 1


def test_different_alert_types_tracked_independently(store):
    now = _now()
    for _ in range(3):
        store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)

    # overdue should still be allowed
    assert store.is_allowed("backup", "overdue", max_count=3, window_seconds=60, now=now) is True


def test_reset_clears_entry(store):
    now = _now()
    for _ in range(3):
        store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now)

    store.reset("backup", "failure")
    assert store.all_entries() == []

    # should be allowed again
    assert store.is_allowed("backup", "failure", max_count=3, window_seconds=60, now=now) is True


def test_state_persisted_to_disk(tmp_path):
    path = str(tmp_path / "rl.json")
    s1 = RateLimitStore(path)
    now = _now()
    s1.is_allowed("myjob", "failure", max_count=5, window_seconds=300, now=now)

    s2 = RateLimitStore(path)
    entries = s2.all_entries()
    assert len(entries) == 1
    assert entries[0].job_name == "myjob"
    assert entries[0].count == 1
