"""Tests for cronwatch.replay"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.replay import (
    ReplayResult,
    find_failed_runs,
    replay_run,
    replay_all_failures,
)
from cronwatch.tracker import JobRun


def _run(job_name: str, succeeded: bool, run_id: str = "abc") -> JobRun:
    r = MagicMock(spec=JobRun)
    r.job_name = job_name
    r.run_id = run_id
    r.is_running = False
    r.succeeded = succeeded
    r.started_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return r


@pytest.fixture
def store():
    s = MagicMock()
    return s


def test_find_failed_runs_returns_only_failures(store):
    store.load.return_value = [
        _run("backup", succeeded=True, run_id="r1"),
        _run("backup", succeeded=False, run_id="r2"),
        _run("backup", succeeded=False, run_id="r3"),
    ]
    result = find_failed_runs(store, "backup")
    assert len(result) == 2
    assert all(not r.succeeded for r in result)


def test_find_failed_runs_empty_when_all_ok(store):
    store.load.return_value = [_run("backup", succeeded=True)]
    assert find_failed_runs(store, "backup") == []


def test_find_failed_runs_skips_running(store):
    running = MagicMock(spec=JobRun)
    running.job_name = "backup"
    running.run_id = "r99"
    running.is_running = True
    running.succeeded = False
    store.load.return_value = [running]
    assert find_failed_runs(store, "backup") == []


def test_replay_run_success():
    run = _run("myjob", succeeded=False, run_id="r1")
    with patch("cronwatch.replay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = replay_run(run, "echo ok")
    assert result.succeeded
    assert result.job_name == "myjob"
    assert result.original_run_id == "r1"
    assert result.stdout == "ok"


def test_replay_run_failure():
    run = _run("myjob", succeeded=False, run_id="r2")
    with patch("cronwatch.replay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        result = replay_run(run, "false")
    assert not result.succeeded
    assert result.returncode == 1


def test_replay_run_timeout():
    run = _run("myjob", succeeded=False, run_id="r3")
    with patch("cronwatch.replay.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
        result = replay_run(run, "sleep 100", timeout=5)
    assert result.returncode == -1
    assert result.stderr == "timeout"


def test_replay_all_failures_calls_replay_for_each(store):
    store.load.return_value = [
        _run("job", succeeded=False, run_id="r1"),
        _run("job", succeeded=False, run_id="r2"),
    ]
    with patch("cronwatch.replay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        results = replay_all_failures(store, "job", "echo x")
    assert len(results) == 2
    assert all(r.succeeded for r in results)


def test_replay_all_failures_returns_empty_when_no_failures(store):
    store.load.return_value = [_run("job", succeeded=True)]
    results = replay_all_failures(store, "job", "echo x")
    assert results == []
