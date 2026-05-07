"""Tests for cronwatch.trends."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.tracker import JobRun
from cronwatch.trends import (
    TrendPoint,
    JobTrend,
    compute_trend,
    compute_all_trends,
    _bucket_key,
)


def _make_run(
    name: str = "backup",
    offset_days: int = 0,
    success: bool = True,
    duration: float = 60.0,
) -> JobRun:
    started = datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=offset_days)
    finished = started + timedelta(seconds=duration)
    run = JobRun(job_name=name, run_id="r1", started_at=started)
    run.finished_at = finished
    run.exit_code = 0 if success else 1
    return run


# ---------------------------------------------------------------------------
# _bucket_key
# ---------------------------------------------------------------------------

def test_bucket_key_daily():
    run = _make_run(offset_days=0)
    assert _bucket_key(run, "daily") == "2024-01-10"


def test_bucket_key_weekly():
    run = _make_run(offset_days=0)
    key = _bucket_key(run, "weekly")
    assert key.startswith("2024-W")


# ---------------------------------------------------------------------------
# compute_trend
# ---------------------------------------------------------------------------

def test_compute_trend_returns_none_for_empty():
    assert compute_trend("backup", []) is None


def test_compute_trend_returns_none_for_unfinished_only():
    run = JobRun(job_name="backup", run_id="r1", started_at=datetime.now(timezone.utc))
    assert compute_trend("backup", [run]) is None


def test_compute_trend_correct_bucket_count():
    runs = [_make_run(offset_days=i) for i in range(3)]
    trend = compute_trend("backup", runs, granularity="daily")
    assert trend is not None
    assert len(trend.points) == 3


def test_compute_trend_success_rate_all_success():
    runs = [_make_run(offset_days=0, success=True) for _ in range(4)]
    trend = compute_trend("backup", runs)
    assert trend.points[0].success_rate == pytest.approx(1.0)


def test_compute_trend_success_rate_mixed():
    runs = [
        _make_run(offset_days=0, success=True),
        _make_run(offset_days=0, success=False),
    ]
    trend = compute_trend("backup", runs)
    assert trend.points[0].success_rate == pytest.approx(0.5)


def test_compute_trend_avg_duration():
    runs = [
        _make_run(offset_days=0, duration=60.0),
        _make_run(offset_days=0, duration=120.0),
    ]
    trend = compute_trend("backup", runs)
    assert trend.points[0].avg_duration == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# JobTrend.improving / degrading
# ---------------------------------------------------------------------------

def test_job_trend_improving():
    pts = [
        TrendPoint(bucket="2024-01-08", avg_duration=60, success_rate=0.5, run_count=2),
        TrendPoint(bucket="2024-01-09", avg_duration=60, success_rate=0.8, run_count=2),
        TrendPoint(bucket="2024-01-10", avg_duration=60, success_rate=1.0, run_count=2),
    ]
    trend = JobTrend(job_name="backup", granularity="daily", points=pts)
    assert trend.improving is True
    assert trend.degrading is False


def test_job_trend_degrading():
    pts = [
        TrendPoint(bucket="2024-01-08", avg_duration=60, success_rate=1.0, run_count=2),
        TrendPoint(bucket="2024-01-09", avg_duration=60, success_rate=0.7, run_count=2),
        TrendPoint(bucket="2024-01-10", avg_duration=60, success_rate=0.4, run_count=2),
    ]
    trend = JobTrend(job_name="backup", granularity="daily", points=pts)
    assert trend.degrading is True
    assert trend.improving is False


# ---------------------------------------------------------------------------
# compute_all_trends
# ---------------------------------------------------------------------------

def test_compute_all_trends_uses_store():
    store = MagicMock()
    store.all_job_names.return_value = ["backup", "sync"]
    store.load.side_effect = lambda name: [_make_run(name=name, offset_days=0)]
    trends = compute_all_trends(store, granularity="daily")
    assert len(trends) == 2
    assert {t.job_name for t in trends} == {"backup", "sync"}


def test_compute_all_trends_skips_empty_jobs():
    store = MagicMock()
    store.all_job_names.return_value = ["empty_job"]
    store.load.return_value = []
    trends = compute_all_trends(store)
    assert trends == []
