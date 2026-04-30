"""Job run tracking: records start/finish events and maintains run history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from cronwatch.config import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class JobRun:
    job_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    alerted: bool = False

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        return self.finished_at is None

    @property
    def succeeded(self) -> bool:
        return self.finished_at is not None and self.exit_code == 0


class JobTracker:
    """Thread-safe-ish in-memory tracker for job runs."""

    def __init__(self, configs: List[JobConfig]):
        self._configs: Dict[str, JobConfig] = {c.name: c for c in configs}
        self._active: Dict[str, JobRun] = {}
        self._history: Dict[str, List[JobRun]] = {name: [] for name in self._configs}

    def start(self, job_name: str, started_at: Optional[datetime] = None) -> Optional[JobRun]:
        if job_name not in self._configs:
            logger.warning("start() called for unknown job '%s'.", job_name)
            return None
        run = JobRun(job_name=job_name, started_at=started_at or datetime.utcnow())
        self._active[job_name] = run
        logger.debug("Job '%s' started at %s.", job_name, run.started_at)
        return run

    def finish(
        self,
        job_name: str,
        exit_code: int = 0,
        finished_at: Optional[datetime] = None,
    ) -> Optional[JobRun]:
        run = self._active.pop(job_name, None)
        if run is None:
            logger.warning("finish() called for job '%s' with no active run.", job_name)
            return None
        run.finished_at = finished_at or datetime.utcnow()
        run.exit_code = exit_code
        self._history[job_name].append(run)
        logger.debug(
            "Job '%s' finished (exit=%d, duration=%.1fs).",
            job_name,
            exit_code,
            run.duration or 0,
        )
        return run

    def last_run(self, job_name: str) -> Optional[JobRun]:
        history = self._history.get(job_name, [])
        return history[-1] if history else None

    def active_run(self, job_name: str) -> Optional[JobRun]:
        return self._active.get(job_name)

    def is_active(self, job_name: str) -> bool:
        return job_name in self._active

    def history(self, job_name: str) -> List[JobRun]:
        return list(self._history.get(job_name, []))
