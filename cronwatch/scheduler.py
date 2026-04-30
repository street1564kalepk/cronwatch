"""Scheduler module: checks tracked jobs against their expected schedules
and triggers alerts for overdue or failed jobs."""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from cronwatch.alerts import AlertDispatcher
from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.tracker import JobTracker

logger = logging.getLogger(__name__)


def is_overdue(job: JobConfig, tracker: JobTracker, now: Optional[datetime] = None) -> bool:
    """Return True if the job has not started within its expected interval."""
    now = now or datetime.utcnow()
    last_run = tracker.last_run(job.name)
    if last_run is None:
        return False  # Never seen; can't determine overdue status yet
    deadline = last_run.started_at + timedelta(seconds=job.interval + job.grace_period)
    return now > deadline and not tracker.is_active(job.name)


def check_running_too_long(job: JobConfig, tracker: JobTracker, now: Optional[datetime] = None) -> bool:
    """Return True if an active run has exceeded max_duration."""
    now = now or datetime.utcnow()
    active = tracker.active_run(job.name)
    if active is None:
        return False
    elapsed = (now - active.started_at).total_seconds()
    return elapsed > job.max_duration


class Scheduler:
    """Periodically inspects all configured jobs and fires alerts as needed."""

    def __init__(self, config: CronwatchConfig, tracker: JobTracker, dispatcher: AlertDispatcher):
        self.config = config
        self.tracker = tracker
        self.dispatcher = dispatcher
        self._running = False

    def check_once(self, now: Optional[datetime] = None) -> None:
        """Run a single pass over all jobs."""
        now = now or datetime.utcnow()
        for job in self.config.jobs:
            last_run = self.tracker.last_run(job.name)

            # Alert on failed last run (only once per run)
            if last_run is not None and not last_run.succeeded and not last_run.alerted:
                logger.info("Job '%s' failed — dispatching alert.", job.name)
                self.dispatcher.send_failure(job, last_run)
                last_run.alerted = True

            # Alert if job is overdue
            if is_overdue(job, self.tracker, now):
                logger.info("Job '%s' is overdue — dispatching alert.", job.name)
                self.dispatcher.send_overdue(job, last_run)

            # Alert if active run is taking too long
            if check_running_too_long(job, self.tracker, now):
                active = self.tracker.active_run(job.name)
                logger.info("Job '%s' is running too long — dispatching alert.", job.name)
                self.dispatcher.send_overdue(job, active)

    def run(self, poll_interval: int = 60) -> None:
        """Block and repeatedly call check_once every poll_interval seconds."""
        self._running = True
        logger.info("Scheduler started (poll interval: %ds).", poll_interval)
        try:
            while self._running:
                self.check_once()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user.")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
