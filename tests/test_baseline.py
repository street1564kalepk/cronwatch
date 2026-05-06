"""Tests for cronwatch.baseline."""

from __future__ import annotations

import datetime
from typing import List

import pytest

from cronwatch.baseline import (
    BaselineStats,
    compute_all_baselines,
    compute_baseline,
)
from cronwatch.tracker import JobRun


def _make_run(duration: float, succeeded: bool = True) -> JobRun:
    now = datetime.datetime.utcnow()
    run = JobRun(job_name="test_job", started_at=now)
    run.finished_at = now + datetime.timedelta(seconds=duration)
    run.exit_code = 0 if succeeded else 1
    return run


@pytest.fixture
def good_runs() -> List[JobRun]:
    return [_make_run(d) for d in [10.0, 12.0, 11.0, 9.5, 10.5, 11.5]]


def test_compute_baseline_returns_none_when_too_few_samples():
    runs = [_make_run(10.0), _make_run(11.0)]
    result = compute_baseline("job", runs, min_samples=5)
    assert result is None


def test_compute_baseline_excludes_failed_runs():
    runs = [_make_run(10.0)] * 3 + [_make_run(10.0, succeeded=False)] * 10
    result = compute_baseline("job", runs, min_samples=5)
    assert result is None


def test_compute_baseline_returns_stats(good_runs):
    stats = compute_baseline("test_job", good_runs, min_samples=5)
    assert stats is not None
    assert stats.job_name == "test_job"
    assert stats.sample_count == 6
    assert stats.mean_duration == pytest.approx(10.75, rel=1e-3)
    assert stats.min_duration == 9.5
    assert stats.max_duration == 12.0


def test_is_anomalous_detects_outlier(good_runs):
    stats = compute_baseline("test_job", good_runs)
    assert stats is not None
    assert stats.is_anomalous(100.0, sigma=2.0) is True


def test_is_anomalous_accepts_normal_value(good_runs):
    stats = compute_baseline("test_job", good_runs)
    assert stats is not None
    assert stats.is_anomalous(11.0, sigma=2.0) is False


def test_is_anomalous_zero_stddev():
    stats = BaselineStats(
        job_name="flat",
        sample_count=5,
        mean_duration=10.0,
        stddev_duration=0.0,
        min_duration=10.0,
        max_duration=10.0,
    )
    assert stats.is_anomalous(999.0) is False


def test_expected_range_bounds(good_runs):
    stats = compute_baseline("test_job", good_runs)
    assert stats is not None
    low, high = stats.expected_range(sigma=2.0)
    assert low < stats.mean_duration < high


def test_compute_all_baselines_skips_insufficient_jobs():
    history = {
        "enough": [_make_run(10.0)] * 6,
        "too_few": [_make_run(10.0)] * 2,
    }
    result = compute_all_baselines(history, min_samples=5)
    assert "enough" in result
    assert "too_few" not in result
