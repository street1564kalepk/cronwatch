"""Tests for cronwatch.tracker."""

import time

import pytest

from cronwatch.config import JobConfig
from cronwatch.tracker import JobRun, JobTracker


@pytest.fixture
def tracker() -> JobTracker:
    return JobTracker()


@pytest.fixture
def job_config() -> JobConfig:
    return JobConfig(name="backup", schedule="0 2 * * *", max_duration=60.0)


def test_start_creates_active_run(tracker: JobTracker) -> None:
    run = tracker.start("backup")
    assert isinstance(run, JobRun)
    assert run.job_name == "backup"
    assert run.is_running
    assert tracker.active_run("backup") is run


def test_finish_moves_run_to_history(tracker: JobTracker) -> None:
    tracker.start("backup")
    run = tracker.finish("backup", exit_code=0)
    assert run is not None
    assert not run.is_running
    assert run.succeeded
    assert tracker.active_run("backup") is None
    assert tracker.last_run("backup") is run


def test_finish_unknown_job_returns_none(tracker: JobTracker) -> None:
    result = tracker.finish("nonexistent")
    assert result is None


def test_duration_is_positive(tracker: JobTracker) -> None:
    tracker.start("backup")
    time.sleep(0.05)
    run = tracker.finish("backup")
    assert run is not None
    assert run.duration is not None
    assert run.duration >= 0.05


def test_is_overdue_false_when_within_limit(tracker: JobTracker, job_config: JobConfig) -> None:
    tracker.start("backup")
    assert not tracker.is_overdue("backup", job_config)


def test_is_overdue_true_when_exceeded(tracker: JobTracker) -> None:
    cfg = JobConfig(name="backup", schedule="0 2 * * *", max_duration=0.01)
    tracker.start("backup")
    time.sleep(0.05)
    assert tracker.is_overdue("backup", cfg)


def test_is_overdue_false_when_no_active_run(tracker: JobTracker, job_config: JobConfig) -> None:
    assert not tracker.is_overdue("backup", job_config)


def test_is_overdue_false_when_no_max_duration(tracker: JobTracker) -> None:
    cfg = JobConfig(name="backup", schedule="0 2 * * *", max_duration=None)
    tracker.start("backup")
    assert not tracker.is_overdue("backup", cfg)


def test_all_active_returns_running_jobs(tracker: JobTracker) -> None:
    tracker.start("job_a")
    tracker.start("job_b")
    active = tracker.all_active()
    assert set(active.keys()) == {"job_a", "job_b"}
