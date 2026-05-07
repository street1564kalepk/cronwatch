"""Tests for cronwatch.audit."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.audit import AuditEvent, AuditStore, filter_events, record


@pytest.fixture
def store(tmp_path: Path) -> AuditStore:
    return AuditStore(tmp_path / "audit.log")


@pytest.fixture
def _event() -> AuditEvent:
    return AuditEvent(
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        event_type="job_started",
        job_name="backup",
        detail="Job backup started",
    )


def test_load_returns_empty_when_file_missing(store: AuditStore) -> None:
    assert store.load() == []


def test_append_and_load_roundtrip(store: AuditStore, _event: AuditEvent) -> None:
    store.append(_event)
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].event_type == "job_started"
    assert loaded[0].job_name == "backup"


def test_append_multiple_events(store: AuditStore, _event: AuditEvent) -> None:
    second = AuditEvent(
        timestamp=datetime(2024, 6, 1, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
        event_type="job_finished",
        job_name="backup",
        detail="Job backup finished",
    )
    store.append(_event)
    store.append(second)
    loaded = store.load()
    assert len(loaded) == 2
    assert loaded[1].event_type == "job_finished"


def test_record_persists_event(store: AuditStore) -> None:
    evt = record(store, "alert_sent", "Overdue alert sent", job_name="sync")
    assert evt.event_type == "alert_sent"
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].detail == "Overdue alert sent"


def test_record_uses_utc_timestamp(store: AuditStore) -> None:
    evt = record(store, "test_event", "details")
    assert evt.timestamp.endswith("+00:00")


def test_filter_events_by_type(_event: AuditEvent) -> None:
    other = AuditEvent(
        timestamp=_event.timestamp,
        event_type="alert_sent",
        job_name="sync",
        detail="alert",
    )
    result = filter_events([_event, other], event_type="job_started")
    assert len(result) == 1
    assert result[0].event_type == "job_started"


def test_filter_events_by_job(_event: AuditEvent) -> None:
    other = AuditEvent(
        timestamp=_event.timestamp,
        event_type="job_started",
        job_name="deploy",
        detail="deploy started",
    )
    result = filter_events([_event, other], job_name="backup")
    assert len(result) == 1
    assert result[0].job_name == "backup"


def test_filter_events_no_criteria_returns_all(_event: AuditEvent) -> None:
    result = filter_events([_event, _event])
    assert len(result) == 2


def test_load_skips_malformed_lines(store: AuditStore, _event: AuditEvent) -> None:
    store.append(_event)
    with store._path.open("a") as fh:
        fh.write("NOT JSON\n")
    loaded = store.load()
    assert len(loaded) == 1
