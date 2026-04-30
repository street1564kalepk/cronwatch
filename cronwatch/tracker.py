"""Job execution tracker — records start/finish times and detects delays."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatch.config import JobConfig


@dataclass
class JobRun:
    job_name: str
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    exit_code: Optional[int] = None

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at

    @property
    def is_running(self) -> bool:
        return self.finished_at is None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


class JobTracker:
    """Tracks in-progress and completed job runs."""

    def __init__(self) -> None:
        self._active: Dict[str, JobRun] = {}
        self._history: Dict[str, list[JobRun]] = {}

    def start(self, job_name: str) -> JobRun:
        run = JobRun(job_name=job_name)
        self._active[job_name] = run
        return run

    def finish(self, job_name: str, exit_code: int = 0) -> Optional[JobRun]:
        run = self._active.pop(job_name, None)
        if run is None:
            return None
        run.finished_at = time.time()
        run.exit_code = exit_code
        self._history.setdefault(job_name, []).append(run)
        return run

    def is_overdue(self, job_name: str, config: JobConfig) -> bool:
        """Return True if the active run exceeds the configured max_duration."""
        run = self._active.get(job_name)
        if run is None or config.max_duration is None:
            return False
        return (time.time() - run.started_at) > config.max_duration

    def active_run(self, job_name: str) -> Optional[JobRun]:
        return self._active.get(job_name)

    def last_run(self, job_name: str) -> Optional[JobRun]:
        history = self._history.get(job_name, [])
        return history[-1] if history else None

    def all_active(self) -> Dict[str, JobRun]:
        return dict(self._active)
