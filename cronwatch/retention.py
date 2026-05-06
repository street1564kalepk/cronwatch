"""Retention policy enforcement for cronwatch history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.history import HistoryStore
from cronwatch.pruner import prune_all_jobs

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Defines how long / how many runs to keep per job."""

    max_age_days: Optional[int] = None
    max_runs_per_job: Optional[int] = None
    job_overrides: dict[str, "RetentionPolicy"] = field(default_factory=dict)

    def effective_for(self, job_name: str) -> "RetentionPolicy":
        """Return the policy that applies to *job_name*, falling back to self."""
        return self.job_overrides.get(job_name, self)


def apply_retention(store: HistoryStore, policy: RetentionPolicy) -> dict[str, int]:
    """Apply *policy* to *store* and return a mapping of job -> runs removed."""
    if policy.max_age_days is None and policy.max_runs_per_job is None:
        logger.debug("No retention criteria configured; skipping.")
        return {}

    removed = prune_all_jobs(
        store,
        max_age_days=policy.max_age_days,
        max_runs=policy.max_runs_per_job,
    )
    for job, count in removed.items():
        if count:
            logger.info("Retention: removed %d run(s) for job '%s'", count, job)
    return removed


def retention_summary(removed: dict[str, int]) -> str:
    """Return a human-readable summary of what was pruned."""
    if not removed:
        return "No runs removed."
    lines = [f"  {job}: {count} run(s) removed" for job, count in sorted(removed.items()) if count]
    if not lines:
        return "No runs removed."
    total = sum(removed.values())
    lines.insert(0, f"Retention applied — {total} total run(s) removed:")
    return "\n".join(lines)
