"""Tests for cronwatch/metrics.py"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwatch.metrics import (
    JobMetrics,
    _compute_job_metrics,
    collect_metrics,
    format_metrics,
)
from cronwatch.tracker import JobRun


def _run(job: str, start: float, end: float, exit_code: int) -> JobRun:
    r = JobRun(job_name=job, start_time=start)
    r.end_time = end
    r.exit_code = exit_code
    return r


# ---------------------------------------------------------------------------
# _compute_job_metrics
# ---------------------------------------------------------------------------

def test_compute_job_metrics_empty_returns_defaults():
    m = _compute_job_metrics("backup", [])
    assert m.job_name == "backup"
    assert m.total_runs == 0
    assert m.last_status is None


def test_compute_job_metrics_counts_correctly():
    runs = [
        _run("backup", 0.0, 10.0, 0),
        _run("backup", 20.0, 35.0, 1),
        _run("backup", 40.0, 50.0, 0),
    ]
    m = _compute_job_metrics("backup", runs)
    assert m.total_runs == 3
    assert m.successful_runs == 2
    assert m.failed_runs == 1


def test_compute_job_metrics_duration_stats():
    runs = [
        _run("backup", 0.0, 10.0, 0),   # 10s
        _run("backup", 20.0, 30.0, 0),  # 10s
        _run("backup", 40.0, 60.0, 0),  # 20s
    ]
    m = _compute_job_metrics("backup", runs)
    assert m.avg_duration_seconds == pytest.approx(40.0 / 3, rel=1e-3)
    assert m.max_duration_seconds == 20.0
    assert m.min_duration_seconds == 10.0


def test_compute_job_metrics_last_status_failure():
    runs = [
        _run("backup", 0.0, 5.0, 0),
        _run("backup", 10.0, 15.0, 2),
    ]
    m = _compute_job_metrics("backup", runs)
    assert m.last_status == "failure"


def test_compute_job_metrics_ignores_running_runs():
    running = JobRun(job_name="backup", start_time=100.0)
    finished = _run("backup", 0.0, 10.0, 0)
    m = _compute_job_metrics("backup", [running, finished])
    assert m.total_runs == 1


# ---------------------------------------------------------------------------
# collect_metrics
# ---------------------------------------------------------------------------

def test_collect_metrics_returns_all_jobs():
    store = MagicMock()
    store.all.return_value = {
        "job_a": [_run("job_a", 0.0, 5.0, 0)],
        "job_b": [_run("job_b", 0.0, 3.0, 1)],
    }
    result = collect_metrics(store)
    assert set(result.keys()) == {"job_a", "job_b"}
    assert result["job_a"].successful_runs == 1
    assert result["job_b"].failed_runs == 1


# ---------------------------------------------------------------------------
# format_metrics
# ---------------------------------------------------------------------------

def test_format_metrics_empty():
    assert format_metrics({}) == "No metrics available."


def test_format_metrics_contains_job_name():
    m = JobMetrics(
        job_name="nightly_backup",
        total_runs=5,
        successful_runs=4,
        failed_runs=1,
        avg_duration_seconds=12.5,
        max_duration_seconds=20.0,
        min_duration_seconds=8.0,
        last_status="success",
    )
    output = format_metrics({"nightly_backup": m})
    assert "nightly_backup" in output
    assert "12.50" in output
