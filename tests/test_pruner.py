"""Tests for cronwatch.pruner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.pruner import prune_all_jobs, prune_by_age, prune_by_count
from cronwatch.tracker import JobRun


def _run(offset_days: int, exit_code: int = 0) -> JobRun:
    started = datetime.now(tz=timezone.utc) - timedelta(days=offset_days)
    finished = started + timedelta(seconds=10)
    return JobRun(
        job_name="backup",
        started_at=started,
        finished_at=finished,
        exit_code=exit_code,
    )


@pytest.fixture()
def store():
    s = MagicMock()
    s.load.return_value = [_run(10), _run(5), _run(1)]
    return s


def test_prune_by_age_removes_old_runs(store):
    removed = prune_by_age(store, "backup", max_age_days=7)
    assert removed == 1
    store.replace.assert_called_once()
    kept = store.replace.call_args[0][1]
    assert len(kept) == 2


def test_prune_by_age_nothing_to_remove(store):
    store.load.return_value = [_run(1), _run(2)]
    removed = prune_by_age(store, "backup", max_age_days=30)
    assert removed == 0
    store.replace.assert_not_called()


def test_prune_by_count_keeps_most_recent(store):
    removed = prune_by_count(store, "backup", max_runs=2)
    assert removed == 1
    kept = store.replace.call_args[0][1]
    assert len(kept) == 2
    # Oldest run (10 days ago) should be gone
    assert all(r.started_at >= _run(5).started_at - timedelta(seconds=1) for r in kept)


def test_prune_by_count_no_excess(store):
    store.load.return_value = [_run(1)]
    removed = prune_by_count(store, "backup", max_runs=5)
    assert removed == 0
    store.replace.assert_not_called()


def test_prune_all_jobs_aggregates(store):
    store.load.return_value = [_run(10), _run(5), _run(1)]
    results = prune_all_jobs(store, ["backup", "sync"], max_age_days=7, max_runs=10)
    assert set(results.keys()) == {"backup", "sync"}
    # Each job had 1 run older than 7 days
    assert results["backup"] == 1
    assert results["sync"] == 1


def test_prune_all_jobs_empty_list(store):
    results = prune_all_jobs(store, [], max_age_days=7)
    assert results == {}
    store.load.assert_not_called()
