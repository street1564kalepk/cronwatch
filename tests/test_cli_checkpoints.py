"""Tests for cronwatch.cli_checkpoints."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_checkpoints import build_checkpoints_parser, run_checkpoints
from cronwatch.checkpoints import CheckpointStore, make_checkpoint


@pytest.fixture()
def subparsers() -> argparse._SubParsersAction:
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_checkpoints_parser_registers_command(
    subparsers: argparse._SubParsersAction,
) -> None:
    build_checkpoints_parser(subparsers)
    parser = argparse.ArgumentParser()
    sp = parser.add_subparsers(dest="cmd")
    build_checkpoints_parser(sp)
    args = parser.parse_args(["checkpoints", "run-1"])
    assert args.run_id == "run-1"


def test_run_checkpoints_no_data_prints_message(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    store_path = tmp_path / "cp.json"
    args = argparse.Namespace(run_id="run-99", store=str(store_path), clear=False)
    with pytest.raises(SystemExit) as exc:
        run_checkpoints(args)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "No checkpoints" in captured.out


def test_run_checkpoints_prints_table(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    store_path = tmp_path / "cp.json"
    s = CheckpointStore(store_path)
    s.record(make_checkpoint("myjob", "run-42", "phase-1", {"rows": "100"}))
    s.record(make_checkpoint("myjob", "run-42", "phase-2"))

    args = argparse.Namespace(run_id="run-42", store=str(store_path), clear=False)
    run_checkpoints(args)
    out = capsys.readouterr().out
    assert "phase-1" in out
    assert "phase-2" in out
    assert "rows=100" in out


def test_run_checkpoints_clear_flag_removes_data(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    store_path = tmp_path / "cp.json"
    s = CheckpointStore(store_path)
    s.record(make_checkpoint("job", "run-7", "step"))

    args = argparse.Namespace(run_id="run-7", store=str(store_path), clear=True)
    run_checkpoints(args)

    reloaded = CheckpointStore(store_path)
    assert reloaded.get("run-7") == []
    out = capsys.readouterr().out
    assert "Cleared" in out
