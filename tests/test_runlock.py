"""Tests for cronwatch.runlock."""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

from cronwatch.runlock import LockEntry, RunLockStore


@pytest.fixture
def store(tmp_path):
    return RunLockStore(path=str(tmp_path / "locks.json"))


def test_load_returns_empty_when_file_missing(store):
    assert store.all_locks() == []


def test_acquire_creates_lock(store):
    entry = store.acquire("backup", pid=1234)
    assert entry.job_name == "backup"
    assert entry.pid == 1234
    assert entry.started_at <= time.time()


def test_acquire_persists_lock(store):
    store.acquire("backup", pid=1234)
    locks = store.all_locks()
    assert len(locks) == 1
    assert locks[0].job_name == "backup"


def test_release_removes_lock(store):
    store.acquire("backup", pid=1234)
    removed = store.release("backup")
    assert removed is True
    assert store.all_locks() == []


def test_release_unknown_job_returns_false(store):
    assert store.release("nonexistent") is False


def test_is_locked_returns_true_for_live_pid(store):
    live_pid = os.getpid()
    store.acquire("myjob", pid=live_pid)
    assert store.is_locked("myjob") is True


def test_is_locked_returns_false_for_dead_pid(store):
    # Use a PID that is almost certainly not running
    store.acquire("myjob", pid=999999)
    with patch("cronwatch.runlock._pid_alive", return_value=False):
        result = store.is_locked("myjob")
    assert result is False


def test_is_locked_cleans_up_stale_lock(store):
    store.acquire("myjob", pid=999999)
    with patch("cronwatch.runlock._pid_alive", return_value=False):
        store.is_locked("myjob")
    # Stale lock should have been auto-removed
    assert store.all_locks() == []


def test_is_locked_returns_false_when_no_lock(store):
    assert store.is_locked("ghost") is False


def test_multiple_jobs_tracked_independently(store):
    store.acquire("job_a", pid=101)
    store.acquire("job_b", pid=102)
    locks = store.all_locks()
    names = {l.job_name for l in locks}
    assert names == {"job_a", "job_b"}


def test_acquire_uses_current_pid_when_none_given(store):
    entry = store.acquire("autojob")
    assert entry.pid == os.getpid()


def test_lock_entry_roundtrip():
    entry = LockEntry(job_name="sync", pid=42, started_at=1_700_000_000.0)
    restored = LockEntry.from_dict(entry.to_dict())
    assert restored == entry
