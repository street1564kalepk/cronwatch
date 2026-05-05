"""Tests for cronwatch.history module."""

import json
import os
from datetime import datetime

import pytest

from cronwatch.history import HistoryStore, _serialize_run, _deserialize_run
from cronwatch.tracker import JobRun


@pytest.fixture
def store(tmp_path):
    return HistoryStore(str(tmp_path / "history.json"))


@pytest.fixture
def finished_run():
    run = JobRun(job_name="backup", started_at=datetime(2024, 1, 10, 2, 0, 0))
    run.finished_at = datetime(2024, 1, 10, 2, 5, 0)
    run.exit_code = 0
    return run


def test_load_returns_empty_when_file_missing(store):
    assert store.load() == []


def test_save_and_load_roundtrip(store, finished_run):
    store.save([finished_run])
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].job_name == "backup"
    assert loaded[0].exit_code == 0
    assert loaded[0].finished_at == finished_run.finished_at


def test_append_adds_to_existing(store, finished_run):
    store.append(finished_run)
    run2 = JobRun(job_name="cleanup", started_at=datetime(2024, 1, 10, 3, 0, 0))
    run2.finished_at = datetime(2024, 1, 10, 3, 1, 0)
    run2.exit_code = 0
    store.append(run2)
    runs = store.load()
    assert len(runs) == 2
    assert runs[1].job_name == "cleanup"


def test_get_runs_for_job_filters_correctly(store, finished_run):
    store.append(finished_run)
    other = JobRun(job_name="other", started_at=datetime(2024, 1, 10, 4, 0, 0))
    other.finished_at = datetime(2024, 1, 10, 4, 1, 0)
    other.exit_code = 0
    store.append(other)
    result = store.get_runs_for_job("backup")
    assert len(result) == 1
    assert result[0].job_name == "backup"


def test_last_run_returns_most_recent(store):
    run1 = JobRun(job_name="job", started_at=datetime(2024, 1, 10, 1, 0, 0))
    run1.finished_at = datetime(2024, 1, 10, 1, 5, 0)
    run1.exit_code = 0
    run2 = JobRun(job_name="job", started_at=datetime(2024, 1, 10, 2, 0, 0))
    run2.finished_at = datetime(2024, 1, 10, 2, 5, 0)
    run2.exit_code = 0
    store.save([run1, run2])
    last = store.last_run("job")
    assert last.started_at == run2.started_at


def test_last_run_returns_none_when_no_finished(store):
    run = JobRun(job_name="job", started_at=datetime(2024, 1, 10, 1, 0, 0))
    store.save([run])
    assert store.last_run("job") is None


def test_load_returns_empty_on_corrupt_file(store):
    with open(store.path, "w") as fh:
        fh.write("not valid json")
    assert store.load() == []


def test_serialize_deserialize_run_without_finish():
    run = JobRun(job_name="nightly", started_at=datetime(2024, 3, 1, 0, 0, 0))
    data = _serialize_run(run)
    assert data["finished_at"] is None
    restored = _deserialize_run(data)
    assert restored.finished_at is None
    assert restored.job_name == "nightly"
