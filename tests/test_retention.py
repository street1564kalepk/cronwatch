"""Tests for cronwatch.retention."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.tracker import JobRun
from cronwatch.history import HistoryStore
from cronwatch.retention import RetentionPolicy, apply_retention, retention_summary


def _run(name: str, days_ago: float, success: bool = True) -> JobRun:
    start = datetime.now(timezone.utc) - timedelta(days=days_ago)
    end = start + timedelta(seconds=30)
    return JobRun(job_name=name, start_time=start, end_time=end, exit_code=0 if success else 1)


@pytest.fixture()
def store(tmp_path):
    s = HistoryStore(str(tmp_path / "history.json"))
    s.append(_run("backup", days_ago=1))
    s.append(_run("backup", days_ago=10))
    s.append(_run("backup", days_ago=20))
    s.append(_run("sync", days_ago=2))
    s.append(_run("sync", days_ago=3))
    return s


def test_apply_retention_by_age(store):
    policy = RetentionPolicy(max_age_days=5)
    removed = apply_retention(store, policy)
    assert removed.get("backup", 0) == 2  # 10-day and 20-day runs removed
    assert removed.get("sync", 0) == 0


def test_apply_retention_by_count(store):
    policy = RetentionPolicy(max_runs_per_job=1)
    removed = apply_retention(store, policy)
    assert removed.get("backup", 0) == 2
    assert removed.get("sync", 0) == 1


def test_apply_retention_no_criteria(store):
    policy = RetentionPolicy()
    removed = apply_retention(store, policy)
    assert removed == {}


def test_effective_for_uses_override():
    override = RetentionPolicy(max_age_days=3)
    policy = RetentionPolicy(max_age_days=30, job_overrides={"backup": override})
    assert policy.effective_for("backup").max_age_days == 3
    assert policy.effective_for("sync").max_age_days == 30


def test_retention_summary_empty():
    assert retention_summary({}) == "No runs removed."


def test_retention_summary_with_removals():
    summary = retention_summary({"backup": 3, "sync": 1})
    assert "4 total" in summary
    assert "backup" in summary
    assert "sync" in summary


def test_retention_summary_all_zero():
    assert retention_summary({"backup": 0}) == "No runs removed."
