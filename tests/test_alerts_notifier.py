"""Integration tests for AlertDispatcher webhook/Slack dispatch paths."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.alerts import AlertDispatcher
from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun


@pytest.fixture
def finished_run():
    run = JobRun(job_name="nightly-backup", started_at=datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc))
    run.finished_at = datetime(2024, 1, 1, 2, 5, tzinfo=timezone.utc)
    run.exit_code = 1
    return run


@pytest.fixture
def running_run():
    run = JobRun(job_name="long-job", started_at=datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc))
    return run


@pytest.fixture
def alert_config_webhook():
    return AlertConfig(
        webhook_url="https://example.com/hook",
        webhook_headers={"Authorization": "Bearer token"},
        slack_webhook_url="https://hooks.slack.com/test",
        slack_channel="#alerts",
    )


def test_send_failure_calls_webhook(finished_run, alert_config_webhook):
    dispatcher = AlertDispatcher(alert_config_webhook)
    with patch("cronwatch.notifier.send_webhook", return_value=True) as mock_wh:
        with patch("cronwatch.notifier.send_slack", return_value=True):
            dispatcher.send_failure(finished_run)
    mock_wh.assert_called_once()
    payload = mock_wh.call_args[0][1]
    assert payload["event"] == "job_failure"
    assert payload["job"] == "nightly-backup"


def test_send_failure_calls_slack(finished_run, alert_config_webhook):
    dispatcher = AlertDispatcher(alert_config_webhook)
    with patch("cronwatch.notifier.send_webhook", return_value=True):
        with patch("cronwatch.notifier.send_slack", return_value=True) as mock_slack:
            dispatcher.send_failure(finished_run)
    mock_slack.assert_called_once()
    msg = mock_slack.call_args[0][1]
    assert "nightly-backup" in msg
    assert "FAILED" in msg


def test_send_overdue_calls_webhook(running_run, alert_config_webhook):
    dispatcher = AlertDispatcher(alert_config_webhook)
    with patch("cronwatch.notifier.send_webhook", return_value=True) as mock_wh:
        with patch("cronwatch.notifier.send_slack", return_value=True):
            dispatcher.send_overdue(running_run, max_seconds=60.0)
    payload = mock_wh.call_args[0][1]
    assert payload["event"] == "job_overdue"
    assert payload["max_seconds"] == 60.0


def test_no_webhook_skips_silently(finished_run):
    cfg = AlertConfig()  # no webhook_url, no slack
    dispatcher = AlertDispatcher(cfg)
    with patch("cronwatch.notifier.send_webhook") as mock_wh:
        with patch("cronwatch.notifier.send_slack") as mock_slack:
            dispatcher.send_failure(finished_run)
    mock_wh.assert_not_called()
    mock_slack.assert_not_called()
