"""Replay module: re-run failed jobs from history and record outcomes."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun

log = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    job_name: str
    original_run_id: str
    replayed_at: datetime
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def find_failed_runs(store: HistoryStore, job_name: str) -> List[JobRun]:
    """Return all failed finished runs for *job_name*."""
    runs = store.load(job_name)
    return [r for r in runs if r.is_running is False and not r.succeeded]


def replay_run(
    run: JobRun,
    command: str,
    timeout: Optional[int] = None,
) -> ReplayResult:
    """Execute *command* and return a ReplayResult tied to *run*."""
    log.info("Replaying job '%s' (run %s)", run.job_name, run.run_id)
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ReplayResult(
            job_name=run.job_name,
            original_run_id=run.run_id,
            replayed_at=datetime.now(timezone.utc),
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        log.warning("Replay of '%s' timed out after %s s", run.job_name, timeout)
        return ReplayResult(
            job_name=run.job_name,
            original_run_id=run.run_id,
            replayed_at=datetime.now(timezone.utc),
            returncode=-1,
            stderr="timeout",
        )


def replay_all_failures(
    store: HistoryStore,
    job_name: str,
    command: str,
    timeout: Optional[int] = None,
) -> List[ReplayResult]:
    """Replay every failed run for *job_name* and return results."""
    failed = find_failed_runs(store, job_name)
    if not failed:
        log.info("No failed runs found for '%s'", job_name)
    return [replay_run(r, command, timeout) for r in failed]
