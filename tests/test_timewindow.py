"""Tests for cronwatch.timewindow."""

from __future__ import annotations

import json
import os
from datetime import datetime, time

import pytest

from cronwatch.timewindow import TimeWindow, TimeWindowStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _at(h: int, m: int, weekday: int = 0) -> datetime:
    """Return a datetime fixed to the given hour/minute and weekday."""
    # 2024-01-01 is a Monday (weekday 0)
    base = datetime(2024, 1, 1 + weekday, h, m)
    return base


@pytest.fixture
def store(tmp_path):
    return TimeWindowStore(str(tmp_path / "windows.json"))


# ---------------------------------------------------------------------------
# TimeWindow.is_active
# ---------------------------------------------------------------------------

def test_is_active_within_window():
    w = TimeWindow("biz", time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
    assert w.is_active(_at(12, 0, weekday=0)) is True


def test_is_active_before_window():
    w = TimeWindow("biz", time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
    assert w.is_active(_at(8, 59, weekday=0)) is False


def test_is_active_at_end_is_exclusive():
    w = TimeWindow("biz", time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
    assert w.is_active(_at(17, 0, weekday=0)) is False


def test_is_active_wrong_day():
    w = TimeWindow("biz", time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
    # weekday=5 → Saturday
    assert w.is_active(_at(12, 0, weekday=5)) is False


def test_overnight_window_before_midnight():
    w = TimeWindow("night", time(22, 0), time(6, 0))
    assert w.is_active(_at(23, 30)) is True


def test_overnight_window_after_midnight():
    w = TimeWindow("night", time(22, 0), time(6, 0))
    assert w.is_active(_at(3, 0)) is True


def test_overnight_window_outside():
    w = TimeWindow("night", time(22, 0), time(6, 0))
    assert w.is_active(_at(10, 0)) is False


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

def test_to_dict_from_dict_roundtrip():
    w = TimeWindow("biz", time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
    assert TimeWindow.from_dict(w.to_dict()) == w


# ---------------------------------------------------------------------------
# TimeWindowStore
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_file_missing(store):
    assert store.all() == []


def test_add_persists_window(store):
    w = TimeWindow("biz", time(9, 0), time(17, 0))
    store.add(w)
    fresh = TimeWindowStore(store._path)
    assert len(fresh.all()) == 1
    assert fresh.all()[0].name == "biz"


def test_add_replaces_existing(store):
    store.add(TimeWindow("biz", time(9, 0), time(17, 0)))
    store.add(TimeWindow("biz", time(8, 0), time(16, 0)))
    assert len(store.all()) == 1
    assert store.get("biz").start == time(8, 0)


def test_remove_returns_true_when_found(store):
    store.add(TimeWindow("biz", time(9, 0), time(17, 0)))
    assert store.remove("biz") is True
    assert store.all() == []


def test_remove_returns_false_when_missing(store):
    assert store.remove("nope") is False


def test_any_active_returns_true_when_one_active(store):
    store.add(TimeWindow("always", time(0, 0), time(0, 0), days=list(range(7))))
    # 00:00 == start, end also 00:00 → overnight wraps, so 00:00 >= start is True
    at = _at(1, 0)
    assert store.any_active(at) is True


def test_any_active_returns_false_when_none_active(store):
    # Window only on Saturday (5), check on Monday (0)
    store.add(TimeWindow("weekend", time(9, 0), time(17, 0), days=[5]))
    assert store.any_active(_at(12, 0, weekday=0)) is False
