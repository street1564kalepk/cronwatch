"""Tests for cronwatch.notifier webhook/Slack helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.notifier import (
    SlackConfig,
    WebhookConfig,
    build_failure_payload,
    build_overdue_payload,
    send_slack,
    send_webhook,
)


@pytest.fixture
def webhook_config():
    return WebhookConfig(url="https://example.com/hook", timeout=5)


@pytest.fixture
def slack_config():
    return SlackConfig(webhook_url="https://hooks.slack.com/test", channel="#ops", timeout=5)


def _mock_response(status: int):
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_send_webhook_success(webhook_config):
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        result = send_webhook(webhook_config, {"event": "test"})
    assert result is True
    mock_open.assert_called_once()


def test_send_webhook_failure_status(webhook_config):
    with patch("urllib.request.urlopen", return_value=_mock_response(500)):
        result = send_webhook(webhook_config, {"event": "test"})
    assert result is False


def test_send_webhook_network_error(webhook_config):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        result = send_webhook(webhook_config, {"event": "test"})
    assert result is False


def test_send_webhook_payload_is_json(webhook_config):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["data"] = json.loads(req.data.decode())
        captured["content_type"] = req.get_header("Content-type")
        return _mock_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        send_webhook(webhook_config, {"key": "value"})

    assert captured["data"] == {"key": "value"}
    assert captured["content_type"] == "application/json"


def test_send_webhook_uses_configured_timeout(webhook_config):
    """Ensure the timeout from WebhookConfig is passed through to urlopen."""
    captured = {}

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        return _mock_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        send_webhook(webhook_config, {"event": "test"})

    assert captured["timeout"] == webhook_config.timeout


def test_send_slack_calls_webhook(slack_config):
    with patch("cronwatch.notifier.send_webhook", return_value=True) as mock_wh:
        result = send_slack(slack_config, "hello")
    assert result is True
    payload = mock_wh.call_args[0][1]
    assert payload["text"] == "hello"
    assert payload["username"] == "cronwatch"
    assert payload["channel"] == "#ops"


def test_build_failure_payload():
    p = build_failure_payload("backup", 1, 42.5)
    assert p["event"] == "job_failure"
    assert p["job"] == "backup"
    assert p["exit_code"] == 1
    assert p["duration_seconds"] == 42.5


def test_build_overdue_payload():
    p = build_overdue_payload("sync", 120.0, 60.0)
    assert p["event"] == "job_overdue"
    assert p["job"] == "sync"
    assert p["running_seconds"] == 120.0
    assert p["max_seconds"] == 60.0
