"""Tests for cronwatch.cli_labels."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_labels import build_labels_parser, run_labels


@pytest.fixture()
def subparsers() -> argparse.Action:
    parser = argparse.ArgumentParser()
    return parser.add_subparsers(dest="command")


def test_build_labels_parser_registers_command(subparsers: argparse.Action) -> None:
    build_labels_parser(subparsers)
    parser = subparsers.choices["labels"]
    assert parser is not None


def _make_index(labels=None, jobs=None, job_labels=None):
    idx = MagicMock()
    idx.all_labels.return_value = labels or []
    idx.jobs_for_label.return_value = jobs or []
    idx.jobs_matching_all.return_value = jobs or []
    idx.labels_for_job.return_value = job_labels or []
    return idx


def _args(**kwargs):
    base = {"config": "cronwatch.yaml", "labels_cmd": "list"}
    base.update(kwargs)
    return argparse.Namespace(**base)


@patch("cronwatch.cli_labels.build_label_index")
@patch("cronwatch.cli_labels.load_config")
def test_run_labels_list(mock_cfg, mock_build, capsys):
    mock_cfg.return_value = MagicMock()
    mock_build.return_value = _make_index(labels=["critical", "storage"])
    run_labels(_args(labels_cmd="list"))
    out = capsys.readouterr().out
    assert "critical" in out
    assert "storage" in out


@patch("cronwatch.cli_labels.build_label_index")
@patch("cronwatch.cli_labels.load_config")
def test_run_labels_list_empty(mock_cfg, mock_build, capsys):
    mock_cfg.return_value = MagicMock()
    mock_build.return_value = _make_index(labels=[])
    run_labels(_args(labels_cmd="list"))
    out = capsys.readouterr().out
    assert "No labels" in out


@patch("cronwatch.cli_labels.build_label_index")
@patch("cronwatch.cli_labels.load_config")
def test_run_labels_jobs_single(mock_cfg, mock_build, capsys):
    mock_cfg.return_value = MagicMock()
    mock_build.return_value = _make_index(jobs=["backup"])
    run_labels(_args(labels_cmd="jobs", label=["critical"]))
    out = capsys.readouterr().out
    assert "backup" in out


@patch("cronwatch.cli_labels.build_label_index")
@patch("cronwatch.cli_labels.load_config")
def test_run_labels_jobs_no_match_exits(mock_cfg, mock_build):
    mock_cfg.return_value = MagicMock()
    mock_build.return_value = _make_index(jobs=[])
    with pytest.raises(SystemExit):
        run_labels(_args(labels_cmd="jobs", label=["ghost"]))


@patch("cronwatch.cli_labels.build_label_index")
@patch("cronwatch.cli_labels.load_config")
def test_run_labels_show(mock_cfg, mock_build, capsys):
    mock_cfg.return_value = MagicMock()
    mock_build.return_value = _make_index(job_labels=["critical", "storage"])
    run_labels(_args(labels_cmd="show", job="backup"))
    out = capsys.readouterr().out
    assert "critical" in out
    assert "storage" in out
