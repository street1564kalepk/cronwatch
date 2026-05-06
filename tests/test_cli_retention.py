"""Tests for cronwatch.cli_retention."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_retention import build_retention_parser, run_retention
from cronwatch.tracker import JobRun


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_retention_parser_registers_command(subparsers):
    build_retention_parser(subparsers)
    parser = argparse.ArgumentParser()
    sp = parser.add_subparsers(dest="cmd")
    build_retention_parser(sp)
    args = parser.parse_args(["retention", "--max-age-days", "7"])
    assert args.max_age_days == 7


def test_run_retention_exits_without_criteria(subparsers, capsys):
    build_retention_parser(subparsers)
    args = argparse.Namespace(
        max_age_days=None,
        max_runs=None,
        config="cronwatch.yaml",
        dry_run=False,
    )
    with pytest.raises(SystemExit) as exc:
        run_retention(args)
    assert exc.value.code == 1


def _make_run(name: str, days_ago: float) -> JobRun:
    start = datetime.now(timezone.utc) - timedelta(days=days_ago)
    end = start + timedelta(seconds=10)
    return JobRun(job_name=name, start_time=start, end_time=end, exit_code=0)


def test_run_retention_calls_apply_retention(tmp_path):
    from cronwatch.history import HistoryStore
    from cronwatch.config import CronwatchConfig, AlertConfig

    history_file = str(tmp_path / "history.json")
    store = HistoryStore(history_file)
    store.append(_make_run("backup", 20))
    store.append(_make_run("backup", 1))

    cfg = MagicMock(spec=CronwatchConfig)
    cfg.history_path = history_file

    args = argparse.Namespace(
        max_age_days=7,
        max_runs=None,
        config="cronwatch.yaml",
        dry_run=False,
    )

    with patch("cronwatch.cli_retention.load_config", return_value=cfg), \
         patch("cronwatch.cli_retention.HistoryStore", return_value=store):
        run_retention(args)

    remaining = store.load().get("backup", [])
    assert len(remaining) == 1


def test_run_retention_dry_run_does_not_modify(tmp_path):
    from cronwatch.history import HistoryStore
    from cronwatch.config import CronwatchConfig

    history_file = str(tmp_path / "history.json")
    store = HistoryStore(history_file)
    store.append(_make_run("sync", 30))
    store.append(_make_run("sync", 1))

    cfg = MagicMock(spec=CronwatchConfig)
    cfg.history_path = history_file

    args = argparse.Namespace(
        max_age_days=7,
        max_runs=None,
        config="cronwatch.yaml",
        dry_run=True,
    )

    with patch("cronwatch.cli_retention.load_config", return_value=cfg), \
         patch("cronwatch.cli_retention.HistoryStore", return_value=store):
        run_retention(args)

    # Dry-run must not have deleted anything
    remaining = store.load().get("sync", [])
    assert len(remaining) == 2
