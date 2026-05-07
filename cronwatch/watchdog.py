"""Watchdog: detect and report jobs that have stopped running entirely.

A job is considered 'missing' if it was expected to run (based on its
max_delay config) but has no recorded run within that window.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.history import HistoryStore
from cronwatch.alerts import AlertDispatcher

logger = logging.getLogger(__name__)


@dataclass
class MissingJobReport:
    job_name: str
    last_seen: Optional[datetime]  # None if never ran
    expected_within_seconds: int
    seconds_overdue: float


def find_missing_jobs(
    config: CronwatchConfig,
    store: HistoryStore,
    now: Optional[datetime] = None,
) -> List[MissingJobReport]:
    """Return a report for every job that has not run within its expected window."""
    if now is None:
        now = datetime.now(timezone.utc)

    reports: List[MissingJobReport] = []

    for job in config.jobs:
        if job.max_delay is None:
            # No expectation configured — skip.
            continue

        history = store.load(job.name)
        finished = [r for r in history if r.end_time is not None]

        if not finished:
            last_seen: Optional[datetime] = None
            seconds_overdue = job.max_delay  # treat as fully overdue
        else:
            last_run = max(finished, key=lambda r: r.end_time)  # type: ignore[arg-type]
            last_seen = last_run.end_time
            elapsed = (now - last_seen).total_seconds()
            seconds_overdue = elapsed - job.max_delay

        if seconds_overdue > 0:
            reports.append(
                MissingJobReport(
                    job_name=job.name,
                    last_seen=last_seen,
                    expected_within_seconds=job.max_delay,
                    seconds_overdue=seconds_overdue,
                )
            )
            logger.warning(
                "Watchdog: job '%s' is %.0fs overdue (last seen: %s)",
                job.name,
                seconds_overdue,
                last_seen.isoformat() if last_seen else "never",
            )

    return reports


def run_watchdog(
    config: CronwatchConfig,
    store: HistoryStore,
    dispatcher: AlertDispatcher,
    now: Optional[datetime] = None,
) -> List[MissingJobReport]:
    """Find missing jobs and dispatch an overdue alert for each one."""
    reports = find_missing_jobs(config, store, now=now)
    for report in reports:
        dispatcher.send_missing(report)
    return reports
