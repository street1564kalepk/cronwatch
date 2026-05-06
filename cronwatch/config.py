"""Configuration loading for cronwatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    schedule: str
    max_duration: int = 3600  # seconds
    alert_on_failure: bool = True
    alert_on_overdue: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_address: str = "cronwatch@localhost"
    webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig]
    alert: AlertConfig = field(default_factory=AlertConfig)
    history_path: str = "cronwatch_history.json"
    silence_path: str = "cronwatch_silence.json"


def load_config(path: str) -> CronwatchConfig:
    with open(path) as fh:
        raw = yaml.safe_load(fh)

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            max_duration=j.get("max_duration", 3600),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_overdue=j.get("alert_on_overdue", True),
            tags=j.get("tags", []),
        )
        for j in raw.get("jobs", [])
    ]

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        email=alert_raw.get("email"),
        smtp_host=alert_raw.get("smtp_host", "localhost"),
        smtp_port=alert_raw.get("smtp_port", 25),
        from_address=alert_raw.get("from_address", "cronwatch@localhost"),
        webhook_url=alert_raw.get("webhook_url"),
        slack_webhook_url=alert_raw.get("slack_webhook_url"),
    )

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        history_path=raw.get("history_path", "cronwatch_history.json"),
        silence_path=raw.get("silence_path", "cronwatch_silence.json"),
    )
