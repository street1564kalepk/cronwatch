"""Tests for cronwatch.alerts."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import AlertDispatcher
from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun


@pytest.fixture
def finished_run() -> JobRun:
    run = JobRun(job_name="nightly_sync", started_at=time.time() - 30)
    run.finished_at = time.time()
    run.exit_code = 1
    return run


@pytest.fixture
def alert_config() -> AlertConfig:
    return AlertConfig(
        email="ops@example.com",
        from_address="cronwatch@example.com",
        smtp_host="localhost",
        smtp_port=25,
    )


def test_send_failure_calls_smtp(alert_config: AlertConfig, finished_run: JobRun) -> None:
    dispatcher = AlertDispatcher(alert_config)
    with patch("cronwatch.alerts.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        dispatcher.send_failure(finished_run)
        mock_smtp.send_message.assert_called_once()


def test_send_overdue_calls_smtp(alert_config: AlertConfig) -> None:
    run = JobRun(job_name="slow_job", started_at=time.time() - 120)
    dispatcher = AlertDispatcher(alert_config)
    with patch("cronwatch.alerts.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        dispatcher.send_overdue(run, max_duration=60.0)
        mock_smtp.send_message.assert_called_once()


def test_no_email_logs_warning(finished_run: JobRun, caplog: pytest.LogCaptureFixture) -> None:
    cfg = AlertConfig(email=None)
    dispatcher = AlertDispatcher(cfg)
    import logging
    with caplog.at_level(logging.WARNING, logger="cronwatch.alerts"):
        dispatcher.send_failure(finished_run)
    assert any("No alert channel" in r.message for r in caplog.records)


def test_email_subject_contains_job_name(
    alert_config: AlertConfig, finished_run: JobRun
) -> None:
    dispatcher = AlertDispatcher(alert_config)
    captured: list = []

    def fake_send(msg):
        captured.append(msg)

    with patch("cronwatch.alerts.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = fake_send
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        dispatcher.send_failure(finished_run)

    assert captured
    assert "nightly_sync" in captured[0]["Subject"]
