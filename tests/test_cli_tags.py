"""Tests for cronwatch.cli_tags."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_tags import build_tags_parser, run_tags


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_tags_parser_registers_command(subparsers):
    build_tags_parser(subparsers)
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd")
    build_tags_parser(subs)
    args = parser.parse_args(["tags"])
    assert args.cmd == "tags"


def _make_config(*jobs):
    cfg = MagicMock()
    cfg.jobs = list(jobs)
    return cfg


def _make_job(name, tags):
    j = MagicMock()
    j.name = name
    j.tags = tags
    return j


def test_run_tags_lists_all_tags(capsys):
    args = MagicMock()
    args.config = "cronwatch.yaml"
    args.tag = None
    config = _make_config(
        _make_job("backup", ["daily"]),
        _make_job("report", ["weekly"]),
    )
    with patch("cronwatch.cli_tags.load_config", return_value=config):
        run_tags(args)
    out = capsys.readouterr().out
    assert "daily" in out
    assert "backup" in out
    assert "weekly" in out


def test_run_tags_filters_by_tag(capsys):
    args = MagicMock()
    args.config = "cronwatch.yaml"
    args.tag = "daily"
    config = _make_config(
        _make_job("backup", ["daily"]),
        _make_job("report", ["weekly"]),
    )
    with patch("cronwatch.cli_tags.load_config", return_value=config):
        run_tags(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "report" not in out


def test_run_tags_unknown_tag_prints_message(capsys):
    args = MagicMock()
    args.config = "cronwatch.yaml"
    args.tag = "ghost"
    config = _make_config(_make_job("backup", ["daily"]))
    with patch("cronwatch.cli_tags.load_config", return_value=config):
        run_tags(args)
    out = capsys.readouterr().out
    assert "No jobs found" in out


def test_run_tags_missing_config_exits(tmp_path):
    args = MagicMock()
    args.config = str(tmp_path / "missing.yaml")
    args.tag = None
    with pytest.raises(SystemExit):
        run_tags(args)
