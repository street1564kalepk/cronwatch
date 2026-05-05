"""Webhook and Slack notification support for cronwatch alerts."""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    url: str
    headers: dict = field(default_factory=dict)
    timeout: int = 10


@dataclass
class SlackConfig:
    webhook_url: str
    channel: Optional[str] = None
    username: str = "cronwatch"
    icon_emoji: str = ":alarm_clock:"
    timeout: int = 10


def send_webhook(config: WebhookConfig, payload: dict) -> bool:
    """POST a JSON payload to a generic webhook URL."""
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", **config.headers}
    req = urllib.request.Request(config.url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            logger.debug("Webhook response: %s", resp.status)
            return resp.status < 400
    except urllib.error.URLError as exc:
        logger.error("Webhook delivery failed: %s", exc)
        return False


def send_slack(config: SlackConfig, message: str) -> bool:
    """Send a message to a Slack incoming webhook."""
    payload: dict = {"text": message, "username": config.username, "icon_emoji": config.icon_emoji}
    if config.channel:
        payload["channel"] = config.channel
    webhook_cfg = WebhookConfig(url=config.webhook_url, timeout=config.timeout)
    return send_webhook(webhook_cfg, payload)


def build_failure_payload(job_name: str, exit_code: int, duration: float) -> dict:
    return {
        "event": "job_failure",
        "job": job_name,
        "exit_code": exit_code,
        "duration_seconds": round(duration, 2),
    }


def build_overdue_payload(job_name: str, running_seconds: float, max_seconds: float) -> dict:
    return {
        "event": "job_overdue",
        "job": job_name,
        "running_seconds": round(running_seconds, 2),
        "max_seconds": round(max_seconds, 2),
    }
