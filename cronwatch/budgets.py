"""Runtime budget tracking: alert when a job exceeds its allowed duration budget."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun

log = logging.getLogger(__name__)


@dataclass
class BudgetPolicy:
    job_name: str
    max_seconds: float
    warn_at_percent: float = 0.8  # warn when run reaches 80% of budget


@dataclass
class BudgetViolation:
    job_name: str
    run_id: str
    budget_seconds: float
    actual_seconds: float

    @property
    def over_by(self) -> float:
        return max(0.0, self.actual_seconds - self.budget_seconds)

    @property
    def percent_used(self) -> float:
        if self.budget_seconds <= 0:
            return 0.0
        return self.actual_seconds / self.budget_seconds

    @property
    def exceeded(self) -> bool:
        return self.actual_seconds > self.budget_seconds


def check_budget(run: JobRun, policy: BudgetPolicy) -> Optional[BudgetViolation]:
    """Return a BudgetViolation if the run breached or approached its budget."""
    if run.end_time is None:
        return None
    dur = (run.end_time - run.start_time).total_seconds()
    threshold = policy.max_seconds * policy.warn_at_percent
    if dur >= threshold:
        return BudgetViolation(
            job_name=run.job_name,
            run_id=run.run_id,
            budget_seconds=policy.max_seconds,
            actual_seconds=dur,
        )
    return None


def check_all_budgets(
    runs: List[JobRun], policies: Dict[str, BudgetPolicy]
) -> List[BudgetViolation]:
    """Check a list of finished runs against their budget policies."""
    violations: List[BudgetViolation] = []
    for run in runs:
        policy = policies.get(run.job_name)
        if policy is None:
            continue
        violation = check_budget(run, policy)
        if violation is not None:
            violations.append(violation)
    return violations


def load_budget_policies(path: Path) -> Dict[str, BudgetPolicy]:
    """Load budget policies from a JSON file keyed by job name."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    policies: Dict[str, BudgetPolicy] = {}
    for job_name, cfg in data.items():
        policies[job_name] = BudgetPolicy(
            job_name=job_name,
            max_seconds=float(cfg["max_seconds"]),
            warn_at_percent=float(cfg.get("warn_at_percent", 0.8)),
        )
    log.debug("Loaded %d budget policies from %s", len(policies), path)
    return policies
