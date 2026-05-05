"""Alert dispatcher: email, webhook, and Slack notifications."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun
from cronwatch import notifier

logger = logging.getLogger(__name__)


class AlertDispatcher:
    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    def send_failure(self, run: JobRun) -> None:
        subject = f"[cronwatch] Job FAILED: {run.job_name}"
        body = (
            f"Job '{run.job_name}' failed.\n"
            f"Exit code: {run.exit_code}\n"
            f"Duration: {run.duration():.1f}s\n"
        )
        self._dispatch(subject, body)
        self._dispatch_webhook_failure(run)
        self._dispatch_slack_failure(run)

    def send_overdue(self, run: JobRun, max_seconds: float) -> None:
        elapsed = run.duration()
        subject = f"[cronwatch] Job OVERDUE: {run.job_name}"
        body = (
            f"Job '{run.job_name}' is still running after {elapsed:.1f}s "
            f"(limit: {max_seconds:.1f}s).\n"
        )
        self._dispatch(subject, body)
        self._dispatch_webhook_overdue(run, max_seconds)
        self._dispatch_slack_overdue(run, max_seconds)

    def _dispatch(self, subject: str, body: str) -> None:
        cfg = self.config
        if not cfg.smtp_host or not cfg.to_addresses:
            logger.warning("No SMTP config; skipping email alert: %s", subject)
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = cfg.from_address or cfg.smtp_user or "cronwatch@localhost"
        msg["To"] = ", ".join(cfg.to_addresses)
        msg.set_content(body)
        try:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as smtp:
                if cfg.smtp_user and cfg.smtp_password:
                    smtp.starttls()
                    smtp.login(cfg.smtp_user, cfg.smtp_password)
                smtp.send_message(msg)
                logger.info("Email alert sent: %s", subject)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send email alert: %s", exc)

    def _dispatch_webhook_failure(self, run: JobRun) -> None:
        if not self.config.webhook_url:
            return
        cfg = notifier.WebhookConfig(
            url=self.config.webhook_url,
            headers=self.config.webhook_headers,
            timeout=self.config.webhook_timeout,
        )
        payload = notifier.build_failure_payload(run.job_name, run.exit_code or -1, run.duration())
        notifier.send_webhook(cfg, payload)

    def _dispatch_webhook_overdue(self, run: JobRun, max_seconds: float) -> None:
        if not self.config.webhook_url:
            return
        cfg = notifier.WebhookConfig(
            url=self.config.webhook_url,
            headers=self.config.webhook_headers,
            timeout=self.config.webhook_timeout,
        )
        payload = notifier.build_overdue_payload(run.job_name, run.duration(), max_seconds)
        notifier.send_webhook(cfg, payload)

    def _dispatch_slack_failure(self, run: JobRun) -> None:
        if not self.config.slack_webhook_url:
            return
        cfg = notifier.SlackConfig(
            webhook_url=self.config.slack_webhook_url,
            channel=self.config.slack_channel,
            username=self.config.slack_username,
            icon_emoji=self.config.slack_icon_emoji,
        )
        msg = f":x: *Job FAILED*: `{run.job_name}` — exit {run.exit_code}, took {run.duration():.1f}s"
        notifier.send_slack(cfg, msg)

    def _dispatch_slack_overdue(self, run: JobRun, max_seconds: float) -> None:
        if not self.config.slack_webhook_url:
            return
        cfg = notifier.SlackConfig(
            webhook_url=self.config.slack_webhook_url,
            channel=self.config.slack_channel,
            username=self.config.slack_username,
            icon_emoji=self.config.slack_icon_emoji,
        )
        msg = (
            f":hourglass_flowing_sand: *Job OVERDUE*: `{run.job_name}` "
            f"running {run.duration():.1f}s / limit {max_seconds:.1f}s"
        )
        notifier.send_slack(cfg, msg)
