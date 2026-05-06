"""Baseline statistics for cron jobs — tracks expected duration ranges."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun


@dataclass
class BaselineStats:
    job_name: str
    sample_count: int
    mean_duration: float
    stddev_duration: float
    min_duration: float
    max_duration: float

    def is_anomalous(self, duration_seconds: float, sigma: float = 2.0) -> bool:
        """Return True if duration deviates more than *sigma* standard deviations."""
        if self.stddev_duration == 0.0:
            return False
        z = abs(duration_seconds - self.mean_duration) / self.stddev_duration
        return z > sigma

    def expected_range(self, sigma: float = 2.0) -> tuple[float, float]:
        """Return (low, high) expected duration bounds."""
        margin = sigma * self.stddev_duration
        return max(0.0, self.mean_duration - margin), self.mean_duration + margin


def compute_baseline(
    job_name: str,
    runs: List[JobRun],
    min_samples: int = 5,
) -> Optional[BaselineStats]:
    """Compute baseline statistics from a list of finished, successful runs.

    Returns None when there are fewer than *min_samples* qualifying runs.
    """
    durations = [
        r.duration
        for r in runs
        if r.succeeded and r.duration is not None
    ]
    if len(durations) < min_samples:
        return None

    return BaselineStats(
        job_name=job_name,
        sample_count=len(durations),
        mean_duration=statistics.mean(durations),
        stddev_duration=statistics.pstdev(durations),
        min_duration=min(durations),
        max_duration=max(durations),
    )


def compute_all_baselines(
    history: Dict[str, List[JobRun]],
    min_samples: int = 5,
) -> Dict[str, BaselineStats]:
    """Compute baselines for every job in *history*."""
    result: Dict[str, BaselineStats] = {}
    for job_name, runs in history.items():
        stats = compute_baseline(job_name, runs, min_samples=min_samples)
        if stats is not None:
            result[job_name] = stats
    return result
