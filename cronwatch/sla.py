"""SLA (Service Level Agreement) tracking for cron jobs."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from cronwatch.history import HistoryStore

logger = logging.getLogger(__name__)


@dataclass
class SLAPolicy:
    job_name: str
    max_failure_rate: float  # 0.0 – 1.0
    max_avg_duration_seconds: float
    window_days: int = 7


@dataclass
class SLAViolation:
    job_name: str
    reason: str
    actual: float
    threshold: float
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        return (
            f"[{self.job_name}] SLA violated – {self.reason}: "
            f"actual={self.actual:.3f}, threshold={self.threshold:.3f}"
        )


def check_sla(policy: SLAPolicy, store: HistoryStore) -> List[SLAViolation]:
    """Return a list of SLA violations for *policy* based on recent history."""
    cutoff = datetime.utcnow() - timedelta(days=policy.window_days)
    runs = [
        r for r in store.load(policy.job_name)
        if r.finished_at is not None and r.finished_at >= cutoff
    ]

    if not runs:
        logger.debug("sla: no finished runs for %s in window", policy.job_name)
        return []

    violations: List[SLAViolation] = []

    failures = sum(1 for r in runs if not r.succeeded())
    failure_rate = failures / len(runs)
    if failure_rate > policy.max_failure_rate:
        violations.append(
            SLAViolation(
                job_name=policy.job_name,
                reason="failure_rate",
                actual=failure_rate,
                threshold=policy.max_failure_rate,
            )
        )

    durations = [r.duration().total_seconds() for r in runs if r.duration() is not None]
    if durations:
        avg_duration = sum(durations) / len(durations)
        if avg_duration > policy.max_avg_duration_seconds:
            violations.append(
                SLAViolation(
                    job_name=policy.job_name,
                    reason="avg_duration_seconds",
                    actual=avg_duration,
                    threshold=policy.max_avg_duration_seconds,
                )
            )

    return violations


def check_all_slas(
    policies: List[SLAPolicy], store: HistoryStore
) -> Dict[str, List[SLAViolation]]:
    """Run SLA checks for every policy and return a mapping of job → violations."""
    return {p.job_name: check_sla(p, store) for p in policies}
