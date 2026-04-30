"""Tests for the cronwatch configuration loader."""

import os
import pytest
import tempfile
import yaml

from cronwatch.config import load_config, CronwatchConfig, JobConfig, AlertConfig


SAMPLE_CONFIG = {
    "check_interval": 60,
    "log_file": "/tmp/cronwatch.log",
    "alert": {
        "email": "ops@example.com",
        "webhook_url": "https://hooks.example.com/notify",
    },
    "jobs": [
        {"name": "backup", "schedule": "0 2 * * *", "timeout": 600, "alert_after": 120},
        {"name": "cleanup", "schedule": "*/15 * * * *"},
    ],
}


@pytest.fixture
def config_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        path = f.name
    yield path
    os.unlink(path)


def test_load_config_returns_correct_type(config_file):
    config = load_config(config_file)
    assert isinstance(config, CronwatchConfig)


def test_load_config_jobs(config_file):
    config = load_config(config_file)
    assert len(config.jobs) == 2
    backup = config.jobs[0]
    assert isinstance(backup, JobConfig)
    assert backup.name == "backup"
    assert backup.schedule == "0 2 * * *"
    assert backup.timeout == 600
    assert backup.alert_after == 120


def test_load_config_job_defaults(config_file):
    config = load_config(config_file)
    cleanup = config.jobs[1]
    assert cleanup.timeout == 300
    assert cleanup.alert_after == 60
    assert cleanup.notify == []


def test_load_config_alert(config_file):
    config = load_config(config_file)
    assert isinstance(config.alert, AlertConfig)
    assert config.alert.email == "ops@example.com"
    assert config.alert.webhook_url == "https://hooks.example.com/notify"
    assert config.alert.slack_channel is None


def test_load_config_top_level_fields(config_file):
    config = load_config(config_file)
    assert config.check_interval == 60
    assert config.log_file == "/tmp/cronwatch.log"


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/cronwatch.yaml")


def test_load_config_missing_required_fields():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"jobs": [{"name": "broken_job"}]}, f)
        path = f.name
    try:
        with pytest.raises(ValueError, match="missing 'name' or 'schedule'"):
            load_config(path)
    finally:
        os.unlink(path)
