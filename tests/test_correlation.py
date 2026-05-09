"""Tests for cronwatch.correlation."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatch.correlation import (
    CorrelationResult,
    _recent_failures,
    correlate_all,
    correlate_failure,
)
from cronwatch.tracker import JobRun


def _run(job: str, exit_code: int = 1, minutes_ago: int = 10) -> JobRun:
    now = datetime.utcnow()
    start = now - timedelta(minutes=minutes_ago + 1)
    end = now - timedelta(minutes=minutes_ago)
    r = JobRun(job_name=job, run_id=f"{job}-1", start_time=start)
    r.end_time = end
    r.exit_code = exit_code
    return r


@pytest.fixture()
def store():
    s = MagicMock()
    s.all_job_names.return_value = ["job_a", "job_b"]
    return s


@pytest.fixture()
def graph():
    g = MagicMock()
    g.dependencies_of.return_value = []
    return g


def test_recent_failures_returns_failed_runs(store):
    store.load.return_value = [_run("job_a", exit_code=1, minutes_ago=5)]
    result = _recent_failures(store, "job_a", timedelta(hours=1))
    assert len(result) == 1


def test_recent_failures_excludes_successes(store):
    store.load.return_value = [_run("job_a", exit_code=0, minutes_ago=5)]
    result = _recent_failures(store, "job_a", timedelta(hours=1))
    assert result == []


def test_recent_failures_excludes_old_runs(store):
    store.load.return_value = [_run("job_a", exit_code=1, minutes_ago=200)]
    result = _recent_failures(store, "job_a", timedelta(hours=1))
    assert result == []


def test_correlate_failure_no_failures_returns_zero_confidence(store, graph):
    store.load.return_value = []
    res = correlate_failure("job_a", store, graph)
    assert res.likely_root_cause is None
    assert res.confidence == 0.0


def test_correlate_failure_no_upstream_returns_unknown(store, graph):
    store.load.return_value = [_run("job_a", exit_code=1)]
    graph.dependencies_of.return_value = []
    res = correlate_failure("job_a", store, graph)
    assert res.likely_root_cause is None
    assert res.upstream_failures == []


def test_correlate_failure_upstream_failure_sets_root_cause(store, graph):
    def _load(name):
        return [_run(name, exit_code=1)]

    store.load.side_effect = _load
    graph.dependencies_of.return_value = ["job_b"]
    res = correlate_failure("job_a", store, graph)
    assert res.likely_root_cause == "job_b"
    assert res.confidence > 0.5
    assert "job_b" in res.upstream_failures


def test_correlate_all_skips_jobs_without_failures(store, graph):
    # job_a has failure, job_b does not
    def _load(name):
        if name == "job_a":
            return [_run(name, exit_code=1)]
        return [_run(name, exit_code=0)]

    store.load.side_effect = _load
    graph.dependencies_of.return_value = []
    results = correlate_all(store, graph)
    assert "job_a" in results
    assert "job_b" not in results


def test_correlate_all_returns_correlation_result_instances(store, graph):
    store.load.return_value = [_run("job_a", exit_code=1)]
    graph.dependencies_of.return_value = []
    results = correlate_all(store, graph)
    for v in results.values():
        assert isinstance(v, CorrelationResult)
