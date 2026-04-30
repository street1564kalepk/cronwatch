"""Tests for cronwatch.scheduler."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.scheduler import Scheduler, check_running_too_long, is_overdue
from cronwatch.tracker import JobRun, JobTracker


@pytest.fixture
def job_config():
    return JobConfig(
        name="backup",
        interval=3600,
        max_duration=600,
        grace_period=120,
    )


@pytest.fixture
def alert_config():
    return AlertConfig(email="ops@example.com", smtp_host="localhost", smtp_port=25)


@pytest.fixture
def cron_config(job_config, alert_config):
    return CronwatchConfig(jobs=[job_config], alert=alert_config)


@pytest.fixture
def tracker():
    return MagicMock(spec=JobTracker)


@pytest.fixture
def dispatcher():
    return MagicMock()


def _make_run(started_at, finished_at=None, exit_code=0, alerted=False):
    run = JobRun(job_name="backup", started_at=started_at)
    if finished_at:
        run.finished_at = finished_at
        run.exit_code = exit_code
    run.alerted = alerted
    return run


def test_is_overdue_returns_false_when_no_last_run(job_config, tracker):
    tracker.last_run.return_value = None
    tracker.is_active.return_value = False
    assert is_overdue(job_config, tracker) is False


def test_is_overdue_returns_true_past_deadline(job_config, tracker):
    started = datetime.utcnow() - timedelta(seconds=job_config.interval + job_config.grace_period + 10)
    tracker.last_run.return_value = _make_run(started, finished_at=started + timedelta(seconds=10))
    tracker.is_active.return_value = False
    assert is_overdue(job_config, tracker) is True


def test_is_overdue_returns_false_within_grace(job_config, tracker):
    started = datetime.utcnow() - timedelta(seconds=job_config.interval - 60)
    tracker.last_run.return_value = _make_run(started, finished_at=started + timedelta(seconds=5))
    tracker.is_active.return_value = False
    assert is_overdue(job_config, tracker) is False


def test_check_running_too_long_true(job_config, tracker):
    started = datetime.utcnow() - timedelta(seconds=job_config.max_duration + 30)
    tracker.active_run.return_value = _make_run(started)
    assert check_running_too_long(job_config, tracker) is True


def test_check_running_too_long_false_when_no_active(job_config, tracker):
    tracker.active_run.return_value = None
    assert check_running_too_long(job_config, tracker) is False


def test_check_once_sends_failure_alert(cron_config, tracker, dispatcher):
    started = datetime.utcnow() - timedelta(seconds=10)
    run = _make_run(started, finished_at=started + timedelta(seconds=5), exit_code=1)
    tracker.last_run.return_value = run
    tracker.is_active.return_value = False
    tracker.active_run.return_value = None

    scheduler = Scheduler(cron_config, tracker, dispatcher)
    scheduler.check_once(now=datetime.utcnow())

    dispatcher.send_failure.assert_called_once()
    assert run.alerted is True


def test_check_once_does_not_double_alert(cron_config, tracker, dispatcher):
    started = datetime.utcnow() - timedelta(seconds=10)
    run = _make_run(started, finished_at=started + timedelta(seconds=5), exit_code=1, alerted=True)
    tracker.last_run.return_value = run
    tracker.is_active.return_value = False
    tracker.active_run.return_value = None

    scheduler = Scheduler(cron_config, tracker, dispatcher)
    scheduler.check_once(now=datetime.utcnow())

    dispatcher.send_failure.assert_not_called()
