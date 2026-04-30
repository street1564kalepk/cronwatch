"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout: int = 300  # seconds
    alert_after: int = 60  # seconds of delay before alerting
    notify: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "/var/log/cronwatch.log"
    check_interval: int = 30  # seconds between checks


def load_config(path: str) -> CronwatchConfig:
    """Load and parse the YAML configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Config file must be a YAML mapping")

    jobs = []
    for job_data in raw.get("jobs", []):
        if "name" not in job_data or "schedule" not in job_data:
            raise ValueError(f"Job entry missing 'name' or 'schedule': {job_data}")
        jobs.append(JobConfig(
            name=job_data["name"],
            schedule=job_data["schedule"],
            timeout=job_data.get("timeout", 300),
            alert_after=job_data.get("alert_after", 60),
            notify=job_data.get("notify", []),
        ))

    alert_data = raw.get("alert", {})
    alert = AlertConfig(
        email=alert_data.get("email"),
        webhook_url=alert_data.get("webhook_url"),
        slack_channel=alert_data.get("slack_channel"),
    )

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        log_file=raw.get("log_file", "/var/log/cronwatch.log"),
        check_interval=raw.get("check_interval", 30),
    )
