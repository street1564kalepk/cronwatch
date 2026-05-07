"""Tests for cronwatch.watchdog."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import JobConfig, AlertConfig, CronwatchConfig
from cronwatch.tracker import JobRun
from cronwatch.watchdog import find_missing_jobs, run_watchdog, MissingJobReport


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _job(name: str, max_delay: int = 3600) -> JobConfig:
    return JobConfig(name=name, command="echo hi", max_delay=max_delay)


def _finished_run(job_name: str, end_offset_seconds: float) -> JobRun:
    """Create a finished run whose end_time is `end_offset_seconds` before NOW."""
    end = NOW - timedelta(seconds=end_offset_seconds)
    start = end - timedelta(seconds=10)
    run = JobRun(job_name=job_name, start_time=start)
    run.end_time = end
    run.exit_code = 0
    return run


@pytest.fixture
def store():
    s = MagicMock()
    s.load.return_value = []
    return s


@pytest.fixture
def config(store):
    job = _job("backup", max_delay=3600)
    return CronwatchConfig(
        jobs=[job],
        alert=AlertConfig(),
    )


def test_no_missing_when_job_ran_recently(config, store):
    store.load.return_value = [_finished_run("backup", end_offset_seconds=100)]
    reports = find_missing_jobs(config, store, now=NOW)
    assert reports == []


def test_missing_when_job_never_ran(config, store):
    store.load.return_value = []
    reports = find_missing_jobs(config, store, now=NOW)
    assert len(reports) == 1
    r = reports[0]
    assert r.job_name == "backup"
    assert r.last_seen is None
    assert r.seconds_overdue >= 3600


def test_missing_when_job_ran_too_long_ago(config, store):
    store.load.return_value = [_finished_run("backup", end_offset_seconds=7200)]
    reports = find_missing_jobs(config, store, now=NOW)
    assert len(reports) == 1
    assert reports[0].seconds_overdue == pytest.approx(3600, abs=1)


def test_job_without_max_delay_is_ignored(store):
    job = JobConfig(name="nolimit", command="echo hi", max_delay=None)
    cfg = CronwatchConfig(jobs=[job], alert=AlertConfig())
    store.load.return_value = []
    reports = find_missing_jobs(cfg, store, now=NOW)
    assert reports == []


def test_run_watchdog_dispatches_alert(config, store):
    store.load.return_value = []
    dispatcher = MagicMock()
    reports = run_watchdog(config, store, dispatcher, now=NOW)
    assert len(reports) == 1
    dispatcher.send_missing.assert_called_once_with(reports[0])


def test_run_watchdog_no_alert_when_on_time(config, store):
    store.load.return_value = [_finished_run("backup", end_offset_seconds=60)]
    dispatcher = MagicMock()
    reports = run_watchdog(config, store, dispatcher, now=NOW)
    assert reports == []
    dispatcher.send_missing.assert_not_called()
