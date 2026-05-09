"""Tests for cronwatch.flapping."""

from __future__ import annotations

import datetime
import os
from pathlib import Path

import pytest

from cronwatch.flapping import (
    FlappingResult,
    _count_transitions,
    detect_all_flapping,
    detect_flapping,
)
from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


def _run(job_name: str, exit_code: int, offset_seconds: int = 0) -> JobRun:
    t = datetime.datetime(2024, 1, 1, 12, 0, 0) + datetime.timedelta(seconds=offset_seconds)
    return JobRun(
        job_name=job_name,
        run_id=f"run-{offset_seconds}",
        started_at=t,
        finished_at=t + datetime.timedelta(seconds=1),
        exit_code=exit_code,
    )


@pytest.fixture
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(str(tmp_path / "history.json"))


# ---------------------------------------------------------------------------
# _count_transitions
# ---------------------------------------------------------------------------

def test_count_transitions_empty():
    assert _count_transitions([]) == 0


def test_count_transitions_single():
    assert _count_transitions([True]) == 0


def test_count_transitions_no_change():
    assert _count_transitions([True, True, True]) == 0


def test_count_transitions_alternating():
    assert _count_transitions([True, False, True, False]) == 3


def test_count_transitions_partial():
    assert _count_transitions([True, True, False, False, True]) == 2


# ---------------------------------------------------------------------------
# detect_flapping
# ---------------------------------------------------------------------------

def test_detect_flapping_returns_none_for_too_few_runs(store: HistoryStore):
    store.append(_run("backup", exit_code=0, offset_seconds=0))
    result = detect_flapping(store, "backup", window=10, threshold=4)
    assert result is None


def test_detect_flapping_stable_job(store: HistoryStore):
    for i in range(8):
        store.append(_run("backup", exit_code=0, offset_seconds=i * 60))
    result = detect_flapping(store, "backup", window=10, threshold=4)
    assert result is not None
    assert result.is_flapping is False
    assert result.transitions == 0


def test_detect_flapping_flapping_job(store: HistoryStore):
    codes = [0, 1, 0, 1, 0, 1, 0, 1]
    for i, code in enumerate(codes):
        store.append(_run("sync", exit_code=code, offset_seconds=i * 60))
    result = detect_flapping(store, "sync", window=10, threshold=4)
    assert result is not None
    assert result.is_flapping is True
    assert result.transitions == 7


def test_detect_flapping_respects_window(store: HistoryStore):
    # First 6 are stable successes, last 2 alternate — below threshold of 4
    codes = [0, 0, 0, 0, 0, 0, 1, 0]
    for i, code in enumerate(codes):
        store.append(_run("etl", exit_code=code, offset_seconds=i * 60))
    result = detect_flapping(store, "etl", window=4, threshold=4)
    assert result is not None
    assert result.is_flapping is False
    assert result.window == 4


# ---------------------------------------------------------------------------
# detect_all_flapping
# ---------------------------------------------------------------------------

def test_detect_all_flapping_returns_only_flapping(store: HistoryStore):
    for i in range(8):
        store.append(_run("stable", exit_code=0, offset_seconds=i))
    codes = [0, 1, 0, 1, 0, 1]
    for i, c in enumerate(codes):
        store.append(_run("flappy", exit_code=c, offset_seconds=i))

    results = detect_all_flapping(store, ["stable", "flappy"], window=10, threshold=4)
    assert len(results) == 1
    assert results[0].job_name == "flappy"


def test_flapping_result_summary_contains_job_name():
    r = FlappingResult(job_name="myjob", transitions=5, window=10, is_flapping=True)
    assert "myjob" in r.summary()
    assert "FLAPPING" in r.summary()
