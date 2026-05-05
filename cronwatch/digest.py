"""Daily digest report generation and delivery for cronwatch."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional

from cronwatch.config import AlertConfig, CronwatchConfig
from cronwatch.history import HistoryStore
from cronwatch.report import all_jobs_summary, format_report

logger = logging.getLogger(__name__)


def build_digest_subject(since: datetime, until: datetime) -> str:
    """Return an email subject line for the digest period."""
    return (
        f"[cronwatch] Daily digest "
        f"{since.strftime('%Y-%m-%d %H:%M')} – {until.strftime('%H:%M')}"
    )


def collect_digest_data(
    store: HistoryStore,
    job_names: list[str],
    since: datetime,
) -> dict:
    """Return summary data for all jobs whose runs fall after *since*."""
    summaries = all_jobs_summary(store, job_names)
    # Filter each job's runs to the digest window
    filtered: dict = {}
    for name, summary in summaries.items():
        runs_in_window = [
            r for r in store.load(name)
            if r.finished_at is not None and r.finished_at >= since
        ]
        filtered[name] = {
            **summary,
            "runs_in_window": len(runs_in_window),
            "failures_in_window": sum(
                1 for r in runs_in_window if not r.succeeded
            ),
        }
    return filtered


def send_digest(
    config: CronwatchConfig,
    store: HistoryStore,
    alert_cfg: AlertConfig,
    since: Optional[datetime] = None,
) -> bool:
    """Send a digest email summarising the last 24 hours of job activity.

    Returns True if the email was dispatched, False otherwise.
    """
    if not alert_cfg.smtp_host or not alert_cfg.to_email:
        logger.warning("Digest skipped: SMTP not configured.")
        return False

    until = datetime.utcnow()
    if since is None:
        since = until - timedelta(hours=24)

    job_names = [job.name for job in config.jobs]
    summaries = collect_digest_data(store, job_names, since)
    body = format_report(summaries)
    subject = build_digest_subject(since, until)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = alert_cfg.from_email or "cronwatch@localhost"
    msg["To"] = alert_cfg.to_email

    try:
        with smtplib.SMTP(alert_cfg.smtp_host, alert_cfg.smtp_port or 25) as smtp:
            smtp.sendmail(msg["From"], [msg["To"]], msg.as_string())
        logger.info("Digest sent to %s", alert_cfg.to_email)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to send digest: %s", exc)
        return False
