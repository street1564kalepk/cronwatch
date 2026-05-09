"""Correlate job failures across dependent jobs to identify root causes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatch.dependencies import DependencyGraph
from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


@dataclass
class CorrelationResult:
    job_name: str
    failed_at: datetime
    likely_root_cause: Optional[str]
    upstream_failures: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0


def _recent_failures(
    store: HistoryStore, job_name: str, window: timedelta
) -> List[JobRun]:
    """Return finished, failed runs within *window* before now."""
    cutoff = datetime.utcnow() - window
    runs = store.load(job_name)
    return [
        r
        for r in runs
        if r.end_time is not None and not r.exit_code == 0 and r.end_time >= cutoff
    ]


def correlate_failure(
    job_name: str,
    store: HistoryStore,
    graph: DependencyGraph,
    window: timedelta = timedelta(hours=1),
) -> CorrelationResult:
    """Analyse whether a job failure is caused by an upstream dependency failure."""
    own_failures = _recent_failures(store, job_name, window)
    if not own_failures:
        return CorrelationResult(job_name=job_name, failed_at=datetime.utcnow(),
                                 likely_root_cause=None, confidence=0.0)

    latest_failure = max(own_failures, key=lambda r: r.end_time)  # type: ignore[arg-type]
    upstream = graph.dependencies_of(job_name)

    upstream_failures: List[str] = []
    for dep in upstream:
        if _recent_failures(store, dep, window):
            upstream_failures.append(dep)

    root_cause: Optional[str] = None
    confidence = 0.0
    if upstream_failures:
        # Prefer the dependency that also has upstream failures (transitive)
        root_cause = upstream_failures[0]
        confidence = min(0.5 + 0.1 * len(upstream_failures), 0.95)

    return CorrelationResult(
        job_name=job_name,
        failed_at=latest_failure.end_time,  # type: ignore[arg-type]
        likely_root_cause=root_cause,
        upstream_failures=upstream_failures,
        confidence=confidence,
    )


def correlate_all(
    store: HistoryStore,
    graph: DependencyGraph,
    window: timedelta = timedelta(hours=1),
) -> Dict[str, CorrelationResult]:
    """Run correlation analysis for every job that has recent failures."""
    results: Dict[str, CorrelationResult] = {}
    for job_name in store.all_job_names():
        failures = _recent_failures(store, job_name, window)
        if failures:
            results[job_name] = correlate_failure(job_name, store, graph, window)
    return results
