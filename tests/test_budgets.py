"""Tests for cronwatch.budgets."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.budgets import (
    BudgetPolicy,
    BudgetViolation,
    check_all_budgets,
    check_budget,
    load_budget_policies,
)
from cronwatch.tracker import JobRun


def _make_run(job_name: str, duration_seconds: float, exit_code: int = 0) -> JobRun:
    start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(seconds=duration_seconds)
    run = JobRun(job_name=job_name, run_id=f"{job_name}-1", start_time=start)
    run.end_time = end
    run.exit_code = exit_code
    return run


@pytest.fixture
def policy() -> BudgetPolicy:
    return BudgetPolicy(job_name="backup", max_seconds=100.0, warn_at_percent=0.8)


def test_check_budget_no_violation(policy):
    run = _make_run("backup", 70.0)
    result = check_budget(run, policy)
    assert result is None


def test_check_budget_warning_threshold(policy):
    run = _make_run("backup", 85.0)  # 85% of 100s budget
    result = check_budget(run, policy)
    assert result is not None
    assert not result.exceeded
    assert result.percent_used == pytest.approx(0.85)


def test_check_budget_exceeded(policy):
    run = _make_run("backup", 120.0)
    result = check_budget(run, policy)
    assert result is not None
    assert result.exceeded
    assert result.over_by == pytest.approx(20.0)


def test_check_budget_still_running(policy):
    start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    run = JobRun(job_name="backup", run_id="backup-1", start_time=start)
    # end_time is None — still running
    result = check_budget(run, policy)
    assert result is None


def test_check_all_budgets_filters_by_policy():
    policies = {
        "backup": BudgetPolicy(job_name="backup", max_seconds=100.0),
    }
    runs = [
        _make_run("backup", 110.0),
        _make_run("sync", 200.0),  # no policy — should be ignored
    ]
    violations = check_all_budgets(runs, policies)
    assert len(violations) == 1
    assert violations[0].job_name == "backup"


def test_check_all_budgets_empty_runs():
    policies = {"backup": BudgetPolicy(job_name="backup", max_seconds=100.0)}
    assert check_all_budgets([], policies) == []


def test_load_budget_policies_missing_file(tmp_path):
    result = load_budget_policies(tmp_path / "nonexistent.json")
    assert result == {}


def test_load_budget_policies_reads_file(tmp_path):
    data = {
        "backup": {"max_seconds": 300, "warn_at_percent": 0.75},
        "sync": {"max_seconds": 60},
    }
    p = tmp_path / "budgets.json"
    p.write_text(json.dumps(data))
    policies = load_budget_policies(p)
    assert len(policies) == 2
    assert policies["backup"].max_seconds == 300.0
    assert policies["backup"].warn_at_percent == 0.75
    assert policies["sync"].warn_at_percent == 0.8  # default


def test_budget_violation_percent_used_zero_budget():
    v = BudgetViolation(job_name="x", run_id="x-1", budget_seconds=0.0, actual_seconds=5.0)
    assert v.percent_used == 0.0
