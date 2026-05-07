"""Trend analysis for cron job duration and success rates over time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


@dataclass
class TrendPoint:
    """A single data point in a trend series."""
    bucket: str          # e.g. "2024-01-15" for daily, "2024-W03" for weekly
    avg_duration: float  # seconds
    success_rate: float  # 0.0 – 1.0
    run_count: int


@dataclass
class JobTrend:
    job_name: str
    granularity: str     # "daily" | "weekly"
    points: List[TrendPoint]

    @property
    def improving(self) -> bool:
        """Return True if success rate is non-decreasing over the last 3 buckets."""
        rates = [p.success_rate for p in self.points[-3:]]
        return len(rates) >= 2 and rates[-1] >= rates[0]

    @property
    def degrading(self) -> bool:
        rates = [p.success_rate for p in self.points[-3:]]
        return len(rates) >= 2 and rates[-1] < rates[0]


def _bucket_key(run: JobRun, granularity: str) -> str:
    if granularity == "weekly":
        return run.started_at.strftime("%Y-W%W")
    return run.started_at.strftime("%Y-%m-%d")


def compute_trend(
    job_name: str,
    runs: List[JobRun],
    granularity: str = "daily",
) -> Optional[JobTrend]:
    """Compute trend data for *job_name* from a list of finished runs."""
    finished = [r for r in runs if r.finished_at is not None]
    if not finished:
        return None

    from collections import defaultdict
    buckets: dict = defaultdict(list)
    for run in finished:
        buckets[_bucket_key(run, granularity)].append(run)

    points: List[TrendPoint] = []
    for key in sorted(buckets):
        bucket_runs = buckets[key]
        durations = [r.duration for r in bucket_runs if r.duration is not None]
        successes = sum(1 for r in bucket_runs if r.succeeded)
        points.append(TrendPoint(
            bucket=key,
            avg_duration=sum(durations) / len(durations) if durations else 0.0,
            success_rate=successes / len(bucket_runs),
            run_count=len(bucket_runs),
        ))

    return JobTrend(job_name=job_name, granularity=granularity, points=points)


def compute_all_trends(
    store: HistoryStore,
    granularity: str = "daily",
) -> List[JobTrend]:
    """Compute trends for every job present in the history store."""
    trends: List[JobTrend] = []
    for job_name in store.all_job_names():
        runs = store.load(job_name)
        trend = compute_trend(job_name, runs, granularity)
        if trend is not None:
            trends.append(trend)
    return trends
