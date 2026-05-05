"""Configuration loading and dataclasses for cronwatch."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    max_duration: int = 3600  # seconds
    alert_on_failure: bool = True
    alert_on_overdue: bool = True


@dataclass
class AlertConfig:
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: list = field(default_factory=list)
    webhook_url: Optional[str] = None
    webhook_headers: dict = field(default_factory=dict)
    webhook_timeout: int = 10
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_username: str = "cronwatch"
    slack_icon_emoji: str = ":alarm_clock:"


@dataclass
class CronwatchConfig:
    jobs: list = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    history_path: str = "~/.cronwatch/history.json"
    check_interval: int = 60


def load_config(path: str) -> CronwatchConfig:
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        smtp_host=alert_raw.get("smtp_host"),
        smtp_port=alert_raw.get("smtp_port", 587),
        smtp_user=alert_raw.get("smtp_user"),
        smtp_password=alert_raw.get("smtp_password"),
        from_address=alert_raw.get("from_address"),
        to_addresses=alert_raw.get("to_addresses", []),
        webhook_url=alert_raw.get("webhook_url"),
        webhook_headers=alert_raw.get("webhook_headers", {}),
        webhook_timeout=alert_raw.get("webhook_timeout", 10),
        slack_webhook_url=alert_raw.get("slack_webhook_url"),
        slack_channel=alert_raw.get("slack_channel"),
        slack_username=alert_raw.get("slack_username", "cronwatch"),
        slack_icon_emoji=alert_raw.get("slack_icon_emoji", ":alarm_clock:"),
    )

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            max_duration=j.get("max_duration", 3600),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_overdue=j.get("alert_on_overdue", True),
        )
        for j in raw.get("jobs", [])
    ]

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        history_path=raw.get("history_path", "~/.cronwatch/history.json"),
        check_interval=raw.get("check_interval", 60),
    )
