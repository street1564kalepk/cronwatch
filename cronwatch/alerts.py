"""Alert dispatcher — sends notifications when jobs fail or run too long."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Dispatches alerts via configured channels."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def send_failure(self, run: JobRun) -> None:
        subject = f"[cronwatch] Job '{run.job_name}' failed (exit {run.exit_code})"
        body = (
            f"Job: {run.job_name}\n"
            f"Exit code: {run.exit_code}\n"
            f"Duration: {run.duration:.1f}s\n"
        )
        self._dispatch(subject, body)

    def send_overdue(self, run: JobRun, max_duration: float) -> None:
        elapsed = run.duration or (run.started_at)
        subject = f"[cronwatch] Job '{run.job_name}' is overdue"
        body = (
            f"Job: {run.job_name}\n"
            f"Max allowed duration: {max_duration}s\n"
            f"Still running after: {elapsed:.1f}s\n"
        )
        self._dispatch(subject, body)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _dispatch(self, subject: str, body: str) -> None:
        if self.config.email:
            self._send_email(subject, body)
        else:
            logger.warning("No alert channel configured — logging only.")
        logger.info("Alert dispatched: %s", subject)

    def _send_email(self, subject: str, body: str) -> None:
        cfg = self.config
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = cfg.from_address or "cronwatch@localhost"
        msg["To"] = cfg.email
        msg.set_content(body)
        try:
            with smtplib.SMTP(cfg.smtp_host or "localhost", cfg.smtp_port or 25) as smtp:
                smtp.send_message(msg)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send alert email: %s", exc)
