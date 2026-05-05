"""Tests for cronwatch.digest and cronwatch.cli_digest."""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.digest import (
    build_digest_subject,
    collect_digest_data,
    send_digest,
)
from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    return HistoryStore(str(tmp_path))


@pytest.fixture()
def finished_run():
    run = JobRun(job_name="backup", started_at=datetime(2024, 1, 1, 3, 0))
    run.finished_at = datetime(2024, 1, 1, 3, 5)
    run.exit_code = 0
    return run


@pytest.fixture()
def alert_config():
    return AlertConfig(
        smtp_host="localhost",
        smtp_port=25,
        from_email="cron@example.com",
        to_email="ops@example.com",
    )


@pytest.fixture()
def cron_config(alert_config):
    return CronwatchConfig(
        jobs=[JobConfig(name="backup", schedule="0 3 * * *", max_duration=600)],
        alert=alert_config,
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_build_digest_subject_contains_dates():
    since = datetime(2024, 6, 1, 2, 0)
    until = datetime(2024, 6, 1, 3, 0)
    subject = build_digest_subject(since, until)
    assert "2024-06-01" in subject
    assert "cronwatch" in subject.lower()


def test_collect_digest_data_counts_runs(store, finished_run):
    store.append("backup", finished_run)
    since = finished_run.finished_at - timedelta(minutes=1)
    data = collect_digest_data(store, ["backup"], since)
    assert data["backup"]["runs_in_window"] == 1
    assert data["backup"]["failures_in_window"] == 0


def test_collect_digest_data_excludes_old_runs(store, finished_run):
    store.append("backup", finished_run)
    since = finished_run.finished_at + timedelta(minutes=1)  # after the run
    data = collect_digest_data(store, ["backup"], since)
    assert data["backup"]["runs_in_window"] == 0


def test_send_digest_calls_smtp(store, cron_config, finished_run):
    store.append("backup", finished_run)
    with patch("cronwatch.digest.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        result = send_digest(cron_config, store, cron_config.alert)
    assert result is True
    mock_smtp.sendmail.assert_called_once()


def test_send_digest_no_smtp_returns_false(store, cron_config):
    bad_alert = AlertConfig(smtp_host=None, to_email=None)
    result = send_digest(cron_config, store, bad_alert)
    assert result is False


def test_run_digest_dry_run_prints(tmp_path, capsys, cron_config, finished_run):
    from cronwatch.cli_digest import run_digest
    from cronwatch.history import HistoryStore

    store = HistoryStore(str(tmp_path))
    store.append("backup", finished_run)

    config_file = tmp_path / "cronwatch.yml"
    config_file.write_text(
        "jobs:\n  - name: backup\n    schedule: '0 3 * * *'\n    max_duration: 600\n"
        "alert:\n  smtp_host: localhost\n  to_email: ops@example.com\n"
    )

    run_digest(["--config", str(config_file), "--history-dir", str(tmp_path), "--dry-run"])
    captured = capsys.readouterr()
    assert "backup" in captured.out
