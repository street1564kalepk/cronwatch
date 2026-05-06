"""Snapshot support: capture and compare point-in-time job status summaries."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class JobSnapshot:
    job_name: str
    total_runs: int
    success_count: int
    failure_count: int
    last_run_at: Optional[str]  # ISO-8601 or None
    last_exit_code: Optional[int]


@dataclass
class Snapshot:
    taken_at: str  # ISO-8601
    jobs: List[JobSnapshot]

    def job(self, name: str) -> Optional[JobSnapshot]:
        for j in self.jobs:
            if j.job_name == name:
                return j
        return None


def take_snapshot(history_store) -> Snapshot:
    """Build a Snapshot from the current contents of a HistoryStore."""
    from cronwatch.report import job_summary

    jobs: List[JobSnapshot] = []
    for job_name, runs in history_store.all().items():
        finished = [r for r in runs if not r.is_running()]
        successes = [r for r in finished if r.succeeded()]
        failures = [r for r in finished if not r.succeeded()]
        last = max(finished, key=lambda r: r.started_at, default=None)
        jobs.append(
            JobSnapshot(
                job_name=job_name,
                total_runs=len(finished),
                success_count=len(successes),
                failure_count=len(failures),
                last_run_at=last.started_at.isoformat() if last else None,
                last_exit_code=last.exit_code if last else None,
            )
        )
    return Snapshot(taken_at=datetime.now(timezone.utc).isoformat(), jobs=jobs)


def save_snapshot(snapshot: Snapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(
            {"taken_at": snapshot.taken_at, "jobs": [asdict(j) for j in snapshot.jobs]},
            fh,
            indent=2,
        )
    log.debug("Snapshot saved to %s", path)


def load_snapshot(path: Path) -> Optional[Snapshot]:
    if not path.exists():
        return None
    with path.open() as fh:
        data = json.load(fh)
    jobs = [JobSnapshot(**j) for j in data["jobs"]]
    return Snapshot(taken_at=data["taken_at"], jobs=jobs)


def diff_snapshots(before: Snapshot, after: Snapshot) -> Dict[str, dict]:
    """Return a dict of job_name -> change dict for jobs that changed."""
    result: Dict[str, dict] = {}
    all_names = {j.job_name for j in before.jobs} | {j.job_name for j in after.jobs}
    for name in sorted(all_names):
        b = before.job(name)
        a = after.job(name)
        if b is None:
            result[name] = {"status": "new", "after": asdict(a)}
        elif a is None:
            result[name] = {"status": "removed", "before": asdict(b)}
        else:
            changes = {}
            for field in ("total_runs", "success_count", "failure_count", "last_exit_code"):
                bv, av = getattr(b, field), getattr(a, field)
                if bv != av:
                    changes[field] = {"before": bv, "after": av}
            if changes:
                result[name] = {"status": "changed", "changes": changes}
    return result
