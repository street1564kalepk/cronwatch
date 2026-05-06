"""Tests for cronwatch.silencer."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.silencer import SilenceRule, SilenceStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def store(tmp_path: Path) -> SilenceStore:
    s = SilenceStore(path=tmp_path / "silences.json")
    s.load()
    return s


def _rule(job: str = "backup", offset_start: int = -1, offset_end: int = 1, reason: str = "maintenance") -> SilenceRule:
    now = _utcnow()
    return SilenceRule(
        job_name=job,
        reason=reason,
        start=now + timedelta(hours=offset_start),
        end=now + timedelta(hours=offset_end),
        created_by="tester",
    )


def test_load_returns_empty_when_file_missing(store: SilenceStore) -> None:
    assert store.all_rules() == []


def test_add_persists_rule(store: SilenceStore) -> None:
    store.add(_rule())
    assert store.path.exists()
    data = json.loads(store.path.read_text())
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"


def test_is_silenced_active_rule(store: SilenceStore) -> None:
    store.add(_rule("deploy"))
    assert store.is_silenced("deploy") is True


def test_is_silenced_unknown_job(store: SilenceStore) -> None:
    store.add(_rule("deploy"))
    assert store.is_silenced("cleanup") is False


def test_is_silenced_expired_rule(store: SilenceStore) -> None:
    past_rule = _rule(offset_start=-3, offset_end=-1)
    store.add(past_rule)
    assert store.is_silenced(past_rule.job_name) is False


def test_remove_expired_cleans_up(store: SilenceStore) -> None:
    store.add(_rule("active_job", offset_start=-1, offset_end=1))
    store.add(_rule("old_job", offset_start=-5, offset_end=-2))
    removed = store.remove_expired()
    assert removed == 1
    assert len(store.all_rules()) == 1
    assert store.all_rules()[0].job_name == "active_job"


def test_active_rules_excludes_expired(store: SilenceStore) -> None:
    store.add(_rule("live", offset_start=-1, offset_end=2))
    store.add(_rule("dead", offset_start=-4, offset_end=-1))
    active = store.active_rules()
    assert len(active) == 1
    assert active[0].job_name == "live"


def test_roundtrip_load(store: SilenceStore) -> None:
    rule = _rule("sync", reason="planned downtime")
    store.add(rule)

    store2 = SilenceStore(path=store.path)
    store2.load()
    assert len(store2.all_rules()) == 1
    loaded = store2.all_rules()[0]
    assert loaded.job_name == "sync"
    assert loaded.reason == "planned downtime"
    assert loaded.created_by == "tester"


def test_silence_rule_is_active_boundary() -> None:
    now = _utcnow()
    rule = SilenceRule(
        job_name="edge",
        reason="test",
        start=now - timedelta(seconds=1),
        end=now + timedelta(seconds=1),
    )
    assert rule.is_active(now) is True
    assert rule.is_active(now + timedelta(hours=2)) is False
