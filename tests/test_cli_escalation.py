"""Tests for cronwatch.cli_escalation."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatch.cli_escalation import build_escalation_parser, run_escalation
from cronwatch.escalation import EscalationStore


@pytest.fixture
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers(dest="command")


def test_build_escalation_parser_registers_command(subparsers) -> None:
    build_escalation_parser(subparsers)
    assert "escalation" in subparsers.choices


def _make_args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    state_file = str(tmp_path / "escalation.json")
    defaults = {
        "state_file": state_file,
        "escalation_cmd": None,
        "job": None,
        "func": run_escalation,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_escalation_show_empty(tmp_path: Path, capsys) -> None:
    args = _make_args(tmp_path)
    run_escalation(args)
    captured = capsys.readouterr()
    assert "No escalation state" in captured.out


def test_run_escalation_show_lists_jobs(tmp_path: Path, capsys) -> None:
    store = EscalationStore(tmp_path / "escalation.json")
    store.record_failure("daily_report", threshold=5)
    store.record_failure("daily_report", threshold=5)

    args = _make_args(tmp_path)
    run_escalation(args)
    captured = capsys.readouterr()
    assert "daily_report" in captured.out
    assert "2" in captured.out


def test_run_escalation_reset(tmp_path: Path, capsys) -> None:
    store = EscalationStore(tmp_path / "escalation.json")
    for _ in range(3):
        store.record_failure("cleanup", threshold=3)
    assert store.is_escalated("cleanup")

    args = _make_args(tmp_path, escalation_cmd="reset", job="cleanup")
    run_escalation(args)
    captured = capsys.readouterr()
    assert "reset" in captured.out.lower()

    reloaded = EscalationStore(tmp_path / "escalation.json")
    assert not reloaded.is_escalated("cleanup")


def test_run_escalation_show_unknown_job_exits(tmp_path: Path) -> None:
    args = _make_args(tmp_path, job="nonexistent")
    with pytest.raises(SystemExit):
        run_escalation(args)
