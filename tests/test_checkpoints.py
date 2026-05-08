"""Tests for cronwatch.checkpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.checkpoints import Checkpoint, CheckpointStore, make_checkpoint


@pytest.fixture()
def store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "checkpoints.json")


@pytest.fixture()
def _cp() -> Checkpoint:
    return make_checkpoint("backup", "run-001", "phase-1", {"rows": "500"})


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    s = CheckpointStore(tmp_path / "missing.json")
    assert s.get("run-001") == []


def test_record_persists_checkpoint(store: CheckpointStore, _cp: Checkpoint) -> None:
    store.record(_cp)
    loaded = store.get("run-001")
    assert len(loaded) == 1
    assert loaded[0].label == "phase-1"
    assert loaded[0].metadata == {"rows": "500"}


def test_record_multiple_checkpoints(store: CheckpointStore) -> None:
    for label in ("start", "middle", "end"):
        store.record(make_checkpoint("job", "run-002", label))
    cps = store.get("run-002")
    assert [c.label for c in cps] == ["start", "middle", "end"]


def test_last_returns_most_recent(store: CheckpointStore) -> None:
    store.record(make_checkpoint("job", "run-003", "alpha"))
    store.record(make_checkpoint("job", "run-003", "beta"))
    last = store.last("run-003")
    assert last is not None
    assert last.label == "beta"


def test_last_returns_none_for_unknown_run(store: CheckpointStore) -> None:
    assert store.last("nonexistent") is None


def test_clear_removes_run_checkpoints(store: CheckpointStore, _cp: Checkpoint) -> None:
    store.record(_cp)
    store.clear("run-001")
    assert store.get("run-001") == []


def test_clear_does_not_affect_other_runs(store: CheckpointStore) -> None:
    store.record(make_checkpoint("job", "run-A", "step"))
    store.record(make_checkpoint("job", "run-B", "step"))
    store.clear("run-A")
    assert store.get("run-B") != []


def test_roundtrip_serialisation(store: CheckpointStore) -> None:
    cp = make_checkpoint("deploy", "run-X", "upload", {"env": "prod"})
    store.record(cp)
    reloaded = CheckpointStore(store._path)
    result = reloaded.get("run-X")[0]
    assert result.job_name == "deploy"
    assert result.label == "upload"
    assert result.metadata == {"env": "prod"}


def test_make_checkpoint_sets_utc_timestamp() -> None:
    cp = make_checkpoint("j", "r", "l")
    assert cp.recorded_at.tzinfo is not None
    assert cp.recorded_at.tzinfo == timezone.utc
