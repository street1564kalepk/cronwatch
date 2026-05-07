"""Collect and expose runtime metrics for cron jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


@dataclass
class JobMetrics:
    job_name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    last_run_at: Optional[float] = None
    last_status: Optional[str] = None


def _compute_job_metrics(job_name: str, runs: List[JobRun]) -> JobMetrics:
    finished = [r for r in runs if r.end_time is not None]
    if not finished:
        return JobMetrics(job_name=job_name)

    durations = [
        r.end_time - r.start_time
        for r in finished
        if r.end_time is not None
    ]
    successful = [r for r in finished if r.exit_code == 0]
    failed = [r for r in finished if r.exit_code != 0]

    last_run = max(finished, key=lambda r: r.start_time)

    return JobMetrics(
        job_name=job_name,
        total_runs=len(finished),
        successful_runs=len(successful),
        failed_runs=len(failed),
        avg_duration_seconds=sum(durations) / len(durations) if durations else 0.0,
        max_duration_seconds=max(durations) if durations else 0.0,
        min_duration_seconds=min(durations) if durations else 0.0,
        last_run_at=last_run.start_time,
        last_status="success" if last_run.exit_code == 0 else "failure",
    )


def collect_metrics(store: HistoryStore) -> Dict[str, JobMetrics]:
    """Return a mapping of job_name -> JobMetrics for all jobs in the store."""
    result: Dict[str, JobMetrics] = {}
    for job_name, runs in store.all().items():
        result[job_name] = _compute_job_metrics(job_name, runs)
    return result


def format_metrics(metrics: Dict[str, JobMetrics]) -> str:
    """Render metrics as a human-readable text table."""
    if not metrics:
        return "No metrics available."

    lines = [
        f"{'Job':<30} {'Total':>6} {'OK':>6} {'Fail':>6} {'Avg(s)':>8} {'Max(s)':>8} {'Last Status':<12}",
        "-" * 82,
    ]
    for m in sorted(metrics.values(), key=lambda x: x.job_name):
        lines.append(
            f"{m.job_name:<30} {m.total_runs:>6} {m.successful_runs:>6} "
            f"{m.failed_runs:>6} {m.avg_duration_seconds:>8.2f} "
            f"{m.max_duration_seconds:>8.2f} {m.last_status or 'n/a':<12}"
        )
    return "\n".join(lines)
