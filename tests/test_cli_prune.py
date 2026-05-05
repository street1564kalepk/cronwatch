"""Tests for cronwatch.cli_prune."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_prune import build_prune_parser, run_prune


@pytest.fixture()
def subparsers():
    root = argparse.ArgumentParser()
    return root.add_subparsers()


def test_build_prune_parser_registers_command(subparsers):
    parser = build_prune_parser(subparsers)
    assert parser is not None


def test_run_prune_exits_without_criteria():
    args = argparse.Namespace(
        config="cronwatch.yml",
        max_age_days=None,
        max_runs=None,
        jobs=None,
    )
    with pytest.raises(SystemExit):
        run_prune(args)


@patch("cronwatch.cli_prune.prune_all_jobs", return_value={"backup": 3, "sync": 0})
@patch("cronwatch.cli_prune.HistoryStore")
@patch("cronwatch.cli_prune.load_config")
def test_run_prune_calls_prune_all_jobs(mock_cfg, mock_store_cls, mock_prune, capsys):
    job1 = MagicMock(name="backup")
    job1.name = "backup"
    job2 = MagicMock(name="sync")
    job2.name = "sync"

    cfg = MagicMock()
    cfg.jobs = [job1, job2]
    cfg.history_path = "/tmp/history.json"
    mock_cfg.return_value = cfg

    args = argparse.Namespace(
        config="cronwatch.yml",
        max_age_days=30,
        max_runs=None,
        jobs=None,
    )
    run_prune(args)

    mock_prune.assert_called_once()
    out = capsys.readouterr().out
    assert "3" in out
    assert "backup" in out


@patch("cronwatch.cli_prune.prune_all_jobs", return_value={"backup": 1})
@patch("cronwatch.cli_prune.HistoryStore")
@patch("cronwatch.cli_prune.load_config")
def test_run_prune_respects_job_filter(mock_cfg, mock_store_cls, mock_prune, capsys):
    cfg = MagicMock()
    cfg.history_path = "/tmp/history.json"
    mock_cfg.return_value = cfg

    args = argparse.Namespace(
        config="cronwatch.yml",
        max_age_days=None,
        max_runs=5,
        jobs=["backup"],
    )
    run_prune(args)

    _, call_kwargs = mock_prune.call_args
    job_names = mock_prune.call_args[0][1]
    assert job_names == ["backup"]
