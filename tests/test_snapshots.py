"""Tests for cronwatch.snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatch.snapshots import (
    JobSnapshot,
    Snapshot,
    diff_snapshots,
    load_snapshot,
    save_snapshot,
    take_snapshot,
)
from cronwatch.tracker import JobRun


def _make_run(job_name: str, exit_code: int = 0, running: bool = False) -> JobRun:
    run = JobRun(job_name=job_name, started_at=datetime.now(timezone.utc))
    if not running:
        run.exit_code = exit_code
        run.finished_at = datetime.now(timezone.utc)
    return run


@pytest.fixture()
def store():
    s = MagicMock()
    s.all.return_value = {
        "backup": [_make_run("backup", 0), _make_run("backup", 1)],
        "sync": [_make_run("sync", 0)],
    }
    return s


def test_take_snapshot_job_count(store):
    snap = take_snapshot(store)
    assert len(snap.jobs) == 2


def test_take_snapshot_success_failure_counts(store):
    snap = take_snapshot(store)
    backup = snap.job("backup")
    assert backup is not None
    assert backup.total_runs == 2
    assert backup.success_count == 1
    assert backup.failure_count == 1


def test_take_snapshot_ignores_running(store):
    store.all.return_value = {"job": [_make_run("job", 0), _make_run("job", running=True)]}
    snap = take_snapshot(store)
    assert snap.job("job").total_runs == 1


def test_save_and_load_roundtrip(tmp_path):
    snap = Snapshot(
        taken_at="2024-01-01T00:00:00+00:00",
        jobs=[JobSnapshot("myjob", 3, 2, 1, "2024-01-01T00:00:00+00:00", 0)],
    )
    out = tmp_path / "snap.json"
    save_snapshot(snap, out)
    loaded = load_snapshot(out)
    assert loaded is not None
    assert loaded.taken_at == snap.taken_at
    assert loaded.job("myjob").failure_count == 1


def test_load_snapshot_missing_file(tmp_path):
    assert load_snapshot(tmp_path / "missing.json") is None


def test_diff_no_changes():
    j = JobSnapshot("j", 1, 1, 0, None, 0)
    before = Snapshot(taken_at="t1", jobs=[j])
    after = Snapshot(taken_at="t2", jobs=[j])
    assert diff_snapshots(before, after) == {}


def test_diff_detects_new_failures():
    before = Snapshot(taken_at="t1", jobs=[JobSnapshot("j", 2, 2, 0, None, 0)])
    after = Snapshot(taken_at="t2", jobs=[JobSnapshot("j", 3, 2, 1, None, 1)])
    diff = diff_snapshots(before, after)
    assert "j" in diff
    assert diff["j"]["status"] == "changed"
    assert "failure_count" in diff["j"]["changes"]


def test_diff_detects_new_job():
    before = Snapshot(taken_at="t1", jobs=[])
    after = Snapshot(taken_at="t2", jobs=[JobSnapshot("new", 1, 1, 0, None, 0)])
    diff = diff_snapshots(before, after)
    assert diff["new"]["status"] == "new"


def test_diff_detects_removed_job():
    before = Snapshot(taken_at="t1", jobs=[JobSnapshot("gone", 1, 1, 0, None, 0)])
    after = Snapshot(taken_at="t2", jobs=[])
    diff = diff_snapshots(before, after)
    assert diff["gone"]["status"] == "removed"
