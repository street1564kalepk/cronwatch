"""Tests for cronwatch.annotations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.annotations import Annotation, AnnotationStore


@pytest.fixture()
def store(tmp_path: Path) -> AnnotationStore:
    return AnnotationStore(tmp_path / "annotations.json")


def _ann(run_id: str = "abc123", job: str = "backup", note: str = "ok") -> Annotation:
    return Annotation(run_id=run_id, job_name=job, note=note, author="tester")


# ---------------------------------------------------------------------------
# load / persistence
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_file_missing(store: AnnotationStore) -> None:
    assert store.all_run_ids() == []


def test_add_persists_annotation(store: AnnotationStore, tmp_path: Path) -> None:
    store.add(_ann())
    reloaded = AnnotationStore(tmp_path / "annotations.json")
    assert len(reloaded.get("abc123")) == 1


def test_get_returns_empty_for_unknown_run(store: AnnotationStore) -> None:
    assert store.get("nonexistent") == []


# ---------------------------------------------------------------------------
# add / get
# ---------------------------------------------------------------------------

def test_get_returns_all_annotations_for_run(store: AnnotationStore) -> None:
    store.add(_ann(note="first"))
    store.add(_ann(note="second"))
    entries = store.get("abc123")
    assert len(entries) == 2
    notes = {e.note for e in entries}
    assert notes == {"first", "second"}


def test_add_multiple_runs_are_independent(store: AnnotationStore) -> None:
    store.add(_ann(run_id="run1", note="note for run1"))
    store.add(_ann(run_id="run2", note="note for run2"))
    assert len(store.get("run1")) == 1
    assert len(store.get("run2")) == 1


# ---------------------------------------------------------------------------
# for_job
# ---------------------------------------------------------------------------

def test_for_job_returns_annotations_across_runs(store: AnnotationStore) -> None:
    store.add(_ann(run_id="r1", job="backup"))
    store.add(_ann(run_id="r2", job="backup"))
    store.add(_ann(run_id="r3", job="sync"))
    result = store.for_job("backup")
    assert len(result) == 2
    assert all(a.job_name == "backup" for a in result)


def test_for_job_returns_empty_for_unknown_job(store: AnnotationStore) -> None:
    store.add(_ann(job="backup"))
    assert store.for_job("sync") == []


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_removes_annotations(store: AnnotationStore) -> None:
    store.add(_ann())
    removed = store.delete("abc123")
    assert removed == 1
    assert store.get("abc123") == []


def test_delete_unknown_run_returns_zero(store: AnnotationStore) -> None:
    assert store.delete("ghost") == 0


# ---------------------------------------------------------------------------
# serialisation round-trip
# ---------------------------------------------------------------------------

def test_annotation_round_trip() -> None:
    original = Annotation(
        run_id="xyz",
        job_name="deploy",
        note="manual trigger",
        author="alice",
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    restored = Annotation.from_dict(original.to_dict())
    assert restored.run_id == original.run_id
    assert restored.note == original.note
    assert restored.created_at == original.created_at
