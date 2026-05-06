"""Tests for cronwatch.cli_snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_snapshot import build_snapshot_parser, run_snapshot
from cronwatch.snapshots import JobSnapshot, Snapshot


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers(dest="command")


def test_build_snapshot_parser_registers_command(subparsers):
    build_snapshot_parser(subparsers)
    parser = subparsers.choices["snapshot"]
    assert parser is not None


def _snap():
    return Snapshot(
        taken_at="2024-06-01T12:00:00+00:00",
        jobs=[JobSnapshot("backup", 5, 4, 1, "2024-06-01T11:00:00+00:00", 0)],
    )


def test_run_snapshot_take(tmp_path):
    out = tmp_path / "snap.json"
    args = argparse.Namespace(
        snapshot_cmd="take",
        history=str(tmp_path / "history.json"),
        output=str(out),
    )
    mock_store = MagicMock()
    mock_store.all.return_value = {}
    with patch("cronwatch.cli_snapshot.HistoryStore", return_value=mock_store), \
         patch("cronwatch.cli_snapshot.take_snapshot", return_value=_snap()) as mock_take, \
         patch("cronwatch.cli_snapshot.save_snapshot") as mock_save:
        run_snapshot(args)
        mock_take.assert_called_once()
        mock_save.assert_called_once()


def test_run_snapshot_show(tmp_path, capsys):
    snap_file = tmp_path / "snap.json"
    args = argparse.Namespace(snapshot_cmd="show", file=str(snap_file), as_json=False)
    with patch("cronwatch.cli_snapshot.load_snapshot", return_value=_snap()):
        run_snapshot(args)
    out = capsys.readouterr().out
    assert "backup" in out


def test_run_snapshot_show_missing(tmp_path, capsys):
    args = argparse.Namespace(snapshot_cmd="show", file="/no/such/file.json", as_json=False)
    with patch("cronwatch.cli_snapshot.load_snapshot", return_value=None), pytest.raises(SystemExit):
        run_snapshot(args)


def test_run_snapshot_diff_no_changes(capsys):
    snap = _snap()
    args = argparse.Namespace(snapshot_cmd="diff", before="a.json", after="b.json", as_json=False)
    with patch("cronwatch.cli_snapshot.load_snapshot", side_effect=[snap, snap]):
        run_snapshot(args)
    assert "No changes" in capsys.readouterr().out


def test_run_snapshot_diff_json_output(capsys):
    before = Snapshot("t1", [JobSnapshot("j", 2, 2, 0, None, 0)])
    after = Snapshot("t2", [JobSnapshot("j", 3, 2, 1, None, 1)])
    args = argparse.Namespace(snapshot_cmd="diff", before="a.json", after="b.json", as_json=True)
    with patch("cronwatch.cli_snapshot.load_snapshot", side_effect=[before, after]):
        run_snapshot(args)
    data = json.loads(capsys.readouterr().out)
    assert "j" in data
