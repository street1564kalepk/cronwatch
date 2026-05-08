"""Generate summary reports from job run history."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


def _success_rate(runs: List[JobRun]) -> float:
    finished = [r for r in runs if r.finished_at is not None]
    if not finished:
        return 0.0
    successes = sum(1 for r in finished if r.exit_code == 0)
    return successes / len(finished) * 100


def _avg_duration(runs: List[JobRun]) -> Optional[float]:
    durations = [
        (r.finished_at - r.started_at).total_seconds()
        for r in runs
        if r.finished_at is not None
    ]
    if not durations:
        return None
    return sum(durations) / len(durations)


def job_summary(store: HistoryStore, job_name: str, since: Optional[datetime] = None) -> dict:
    """Return a summary dict for a single job."""
    runs = store.get_runs_for_job(job_name)
    if since:
        runs = [r for r in runs if r.started_at >= since]
    return {
        "job_name": job_name,
        "total_runs": len(runs),
        "success_rate": round(_success_rate(runs), 2),
        "avg_duration_seconds": _avg_duration(runs),
        "last_run": store.last_run(job_name),
    }


def all_jobs_summary(store: HistoryStore, since: Optional[datetime] = None) -> List[dict]:
    """Return summaries for every distinct job in history."""
    runs = store.load()
    job_names = sorted({r.job_name for r in runs})
    return [job_summary(store, name, since=since) for name in job_names]


def failing_jobs(store: HistoryStore, since: Optional[datetime] = None, threshold: float = 100.0) -> List[dict]:
    """Return summaries for jobs whose success rate is below the given threshold.

    Args:
        store: The history store to query.
        since: If provided, only consider runs on or after this datetime.
        threshold: Success rate percentage below which a job is considered failing.
                   Defaults to 100.0, returning any job with at least one failure.

    Returns:
        A list of job summary dicts sorted by success rate ascending.
    """
    summaries = all_jobs_summary(store, since=since)
    failing = [s for s in summaries if s["success_rate"] < threshold]
    return sorted(failing, key=lambda s: s["success_rate"])


def format_report(summaries: List[dict]) -> str:
    """Format a list of job summaries as a human-readable string."""
    if not summaries:
        return "No job history found."
    lines = ["CronWatch Job Report", "=" * 40]
    for s in summaries:
        last = s["last_run"]
        last_str = last.started_at.strftime("%Y-%m-%d %H:%M") if last else "never"
        avg = s["avg_duration_seconds"]
        avg_str = f"{avg:.1f}s" if avg is not None else "n/a"
        lines.append(
            f"{s['job_name']}: runs={s['total_runs']} "
            f"success={s['success_rate']}% avg={avg_str} last={last_str}"
        )
    return "\n".join(lines)
