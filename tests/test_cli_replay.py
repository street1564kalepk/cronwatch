"""Tests for cronwatch.cli_replay"""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_replay import build_replay_parser, run_replay
from cronwatch.replay import ReplayResult
from datetime import datetime, timezone


@pytest.fixture
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_replay_parser_registers_command(subparsers):
    build_replay_parser(subparsers)
    choices = subparsers.choices
    assert "replay" in choices


def _make_args(**kwargs):
    defaults = dict(
        job="backup",
        command="echo re",
        config="cronwatch.yaml",
        timeout=None,
        dry_run=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _result(succeeded: bool, run_id: str = "r1") -> ReplayResult:
    return ReplayResult(
        job_name="backup",
        original_run_id=run_id,
        replayed_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        returncode=0 if succeeded else 1,
        stdout="",
        stderr="" if succeeded else "oops",
    )


def test_run_replay_dry_run_lists_failures(capsys):
    args = _make_args(dry_run=True)
    mock_run = MagicMock(run_id="r1", started_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    with (
        patch("cronwatch.cli_replay.load_config"),
        patch("cronwatch.cli_replay.HistoryStore"),
        patch("cronwatch.cli_replay.find_failed_runs", return_value=[mock_run]),
    ):
        run_replay(args)
    out = capsys.readouterr().out
    assert "r1" in out


def test_run_replay_dry_run_no_failures(capsys):
    args = _make_args(dry_run=True)
    with (
        patch("cronwatch.cli_replay.load_config"),
        patch("cronwatch.cli_replay.HistoryStore"),
        patch("cronwatch.cli_replay.find_failed_runs", return_value=[]),
    ):
        run_replay(args)
    out = capsys.readouterr().out
    assert "No failed" in out


def test_run_replay_nothing_to_replay(capsys):
    args = _make_args()
    with (
        patch("cronwatch.cli_replay.load_config"),
        patch("cronwatch.cli_replay.HistoryStore"),
        patch("cronwatch.cli_replay.replay_all_failures", return_value=[]),
    ):
        run_replay(args)
    out = capsys.readouterr().out
    assert "Nothing to replay" in out


def test_run_replay_all_success(capsys):
    args = _make_args()
    results = [_result(True, "r1"), _result(True, "r2")]
    with (
        patch("cronwatch.cli_replay.load_config"),
        patch("cronwatch.cli_replay.HistoryStore"),
        patch("cronwatch.cli_replay.replay_all_failures", return_value=results),
    ):
        run_replay(args)
    out = capsys.readouterr().out
    assert "2 run(s)" in out
    assert "2 succeeded" in out


def test_run_replay_exits_nonzero_on_failure():
    args = _make_args()
    results = [_result(False, "r1")]
    with (
        patch("cronwatch.cli_replay.load_config"),
        patch("cronwatch.cli_replay.HistoryStore"),
        patch("cronwatch.cli_replay.replay_all_failures", return_value=results),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_replay(args)
    assert exc_info.value.code == 1
