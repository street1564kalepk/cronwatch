"""Tests for cronwatch.sla."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatch.sla import SLAPolicy, SLAViolation, check_sla, check_all_slas
from cronwatch.tracker import JobRun


def _run(
    job: str,
    exit_code: int,
    duration_s: float,
    age_days: float = 0,
) -> JobRun:
    finished = datetime.utcnow() - timedelta(days=age_days)
    started = finished - timedelta(seconds=duration_s)
    return JobRun(
        job_name=job,
        started_at=started,
        finished_at=finished,
        exit_code=exit_code,
        run_id="test",
    )


@pytest.fixture()
def store():
    return MagicMock()


@pytest.fixture()
def policy():
    return SLAPolicy(
        job_name="backup",
        max_failure_rate=0.2,
        max_avg_duration_seconds=120.0,
        window_days=7,
    )


def test_check_sla_no_violations(store, policy):
    store.load.return_value = [_run("backup", 0, 60)]
    violations = check_sla(policy, store)
    assert violations == []


def test_check_sla_failure_rate_violation(store, policy):
    store.load.return_value = [
        _run("backup", 1, 30),
        _run("backup", 1, 30),
        _run("backup", 0, 30),
    ]
    violations = check_sla(policy, store)
    reasons = [v.reason for v in violations]
    assert "failure_rate" in reasons


def test_check_sla_duration_violation(store, policy):
    store.load.return_value = [_run("backup", 0, 300)]
    violations = check_sla(policy, store)
    reasons = [v.reason for v in violations]
    assert "avg_duration_seconds" in reasons


def test_check_sla_excludes_old_runs(store, policy):
    store.load.return_value = [
        _run("backup", 1, 30, age_days=10),  # outside 7-day window
    ]
    violations = check_sla(policy, store)
    assert violations == []


def test_check_sla_empty_history_returns_no_violations(store, policy):
    store.load.return_value = []
    assert check_sla(policy, store) == []


def test_violation_summary_contains_job_name():
    v = SLAViolation(job_name="myjob", reason="failure_rate", actual=0.5, threshold=0.1)
    assert "myjob" in v.summary()
    assert "failure_rate" in v.summary()


def test_check_all_slas_aggregates_results(store, policy):
    store.load.return_value = [_run("backup", 0, 60)]
    results = check_all_slas([policy], store)
    assert "backup" in results
    assert isinstance(results["backup"], list)
