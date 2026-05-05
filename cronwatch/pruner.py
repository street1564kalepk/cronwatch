"""History pruning utilities for cronwatch.

Provides functionality to remove old job run records from the history
based on age or maximum record count per job.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun

logger = logging.getLogger(__name__)


def prune_by_age(store: HistoryStore, job_name: str, max_age_days: int) -> int:
    """Remove runs older than *max_age_days* for *job_name*.

    Returns the number of records removed.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
    runs = store.load(job_name)
    kept = [r for r in runs if r.started_at >= cutoff]
    removed = len(runs) - len(kept)
    if removed:
        store.replace(job_name, kept)
        logger.info("Pruned %d old run(s) for job '%s' (older than %d days).",
                    removed, job_name, max_age_days)
    return removed


def prune_by_count(store: HistoryStore, job_name: str, max_runs: int) -> int:
    """Keep only the *max_runs* most-recent runs for *job_name*.

    Returns the number of records removed.
    """
    runs = store.load(job_name)
    if len(runs) <= max_runs:
        return 0
    kept = sorted(runs, key=lambda r: r.started_at)[-max_runs:]
    removed = len(runs) - len(kept)
    store.replace(job_name, kept)
    logger.info("Pruned %d excess run(s) for job '%s' (kept last %d).",
                removed, job_name, max_runs)
    return removed


def prune_all_jobs(
    store: HistoryStore,
    job_names: list[str],
    max_age_days: Optional[int] = None,
    max_runs: Optional[int] = None,
) -> dict[str, int]:
    """Prune history for every job in *job_names*.

    Applies age-based pruning first, then count-based pruning.
    Returns a mapping of job_name -> total records removed.
    """
    results: dict[str, int] = {}
    for name in job_names:
        total = 0
        if max_age_days is not None:
            total += prune_by_age(store, name, max_age_days)
        if max_runs is not None:
            total += prune_by_count(store, name, max_runs)
        results[name] = total
    return results
