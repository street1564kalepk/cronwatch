"""Tests for cronwatch.cli_audit."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.audit import AuditEvent, AuditStore
from cronwatch.cli_audit import build_audit_parser, run_audit


@pytest.fixture
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_audit_parser_registers_command(subparsers) -> None:
    build_audit_parser(subparsers)
    parser = argparse.ArgumentParser()
    sp = parser.add_subparsers(dest="cmd")
    build_audit_parser(sp)
    args = parser.parse_args(["audit"])
    assert args.cmd == "audit"


def _make_args(log_path: str, **kwargs) -> argparse.Namespace:
    defaults = dict(log=log_path, event_type=None, job=None, tail=0)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_audit_prints_no_events_when_file_missing(tmp_path: Path, capsys) -> None:
    args = _make_args(str(tmp_path / "audit.log"))
    run_audit(args)
    out = capsys.readouterr().out
    assert "No audit events found" in out


def test_run_audit_prints_events(tmp_path: Path, capsys) -> None:
    store = AuditStore(tmp_path / "audit.log")
    store.append(
        AuditEvent(
            timestamp="2024-06-01T12:00:00+00:00",
            event_type="job_started",
            job_name="backup",
            detail="started",
        )
    )
    args = _make_args(str(tmp_path / "audit.log"))
    run_audit(args)
    out = capsys.readouterr().out
    assert "job_started" in out
    assert "backup" in out


def test_run_audit_filters_by_event_type(tmp_path: Path, capsys) -> None:
    store = AuditStore(tmp_path / "audit.log")
    for et in ("job_started", "alert_sent"):
        store.append(
            AuditEvent(
                timestamp="2024-06-01T12:00:00+00:00",
                event_type=et,
                job_name="sync",
                detail=et,
            )
        )
    args = _make_args(str(tmp_path / "audit.log"), event_type="alert_sent")
    run_audit(args)
    out = capsys.readouterr().out
    assert "alert_sent" in out
    assert "job_started" not in out


def test_run_audit_tail_limits_output(tmp_path: Path, capsys) -> None:
    store = AuditStore(tmp_path / "audit.log")
    for i in range(5):
        store.append(
            AuditEvent(
                timestamp=f"2024-06-0{i+1}T12:00:00+00:00",
                event_type="job_finished",
                job_name="job",
                detail=f"run {i}",
            )
        )
    args = _make_args(str(tmp_path / "audit.log"), tail=2)
    run_audit(args)
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if "run" in l]
    assert len(lines) == 2


def test_run_audit_no_match_prints_message(tmp_path: Path, capsys) -> None:
    store = AuditStore(tmp_path / "audit.log")
    store.append(
        AuditEvent(
            timestamp="2024-06-01T12:00:00+00:00",
            event_type="job_started",
            job_name="backup",
            detail="started",
        )
    )
    args = _make_args(str(tmp_path / "audit.log"), job="nonexistent")
    run_audit(args)
    out = capsys.readouterr().out
    assert "No events match" in out
