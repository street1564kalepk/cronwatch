"""Persistent history storage for cron job runs."""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from cronwatch.tracker import JobRun

logger = logging.getLogger(__name__)

DATE_FMT = "%Y-%m-%dT%H:%M:%S.%f"


def _serialize_run(run: JobRun) -> dict:
    return {
        "job_name": run.job_name,
        "started_at": run.started_at.strftime(DATE_FMT),
        "finished_at": run.finished_at.strftime(DATE_FMT) if run.finished_at else None,
        "exit_code": run.exit_code,
    }


def _deserialize_run(data: dict) -> JobRun:
    run = JobRun(
        job_name=data["job_name"],
        started_at=datetime.strptime(data["started_at"], DATE_FMT),
    )
    if data.get("finished_at"):
        run.finished_at = datetime.strptime(data["finished_at"], DATE_FMT)
    run.exit_code = data.get("exit_code")
    return run


class HistoryStore:
    """Reads and writes job run history to a JSON file."""

    def __init__(self, path: str) -> None:
        self.path = path

    def load(self) -> List[JobRun]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r") as fh:
                raw = json.load(fh)
            return [_deserialize_run(r) for r in raw]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load history from %s: %s", self.path, exc)
            return []

    def save(self, runs: List[JobRun]) -> None:
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as fh:
                json.dump([_serialize_run(r) for r in runs], fh, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            logger.error("Failed to save history to %s: %s", self.path, exc)

    def append(self, run: JobRun) -> None:
        runs = self.load()
        runs.append(run)
        self.save(runs)

    def get_runs_for_job(self, job_name: str) -> List[JobRun]:
        return [r for r in self.load() if r.job_name == job_name]

    def last_run(self, job_name: str) -> Optional[JobRun]:
        runs = self.get_runs_for_job(job_name)
        finished = [r for r in runs if r.finished_at is not None]
        return finished[-1] if finished else None
