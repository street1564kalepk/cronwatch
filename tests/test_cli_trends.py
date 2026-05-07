"""Tests for cronwatch.cli_trends."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_trends import build_trends_parser, run_trends, _format_trend
from cronwatch.trends import JobTrend, TrendPoint


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_trends_parser_registers_command(subparsers):
    build_trends_parser(subparsers)
    parser = argparse.ArgumentParser()
    sp = parser.add_subparsers(dest="cmd")
    build_trends_parser(sp)
    args = parser.parse_args(["trends"])
    assert args.cmd == "trends"


def test_build_trends_parser_defaults(subparsers):
    build_trends_parser(subparsers)
    parser = argparse.ArgumentParser()
    sp = parser.add_subparsers(dest="cmd")
    build_trends_parser(sp)
    args = parser.parse_args(["trends"])
    assert args.granularity == "daily"
    assert args.job is None
    assert args.last is None


def _make_trend(job_name: str = "backup") -> JobTrend:
    pts = [
        TrendPoint(bucket="2024-01-10", avg_duration=55.0, success_rate=1.0, run_count=3),
        TrendPoint(bucket="2024-01-11", avg_duration=60.0, success_rate=0.67, run_count=3),
    ]
    return JobTrend(job_name=job_name, granularity="daily", points=pts)


def test_format_trend_contains_job_name():
    trend = _make_trend("nightly-backup")
    output = _format_trend(trend, last=None)
    assert "nightly-backup" in output


def test_format_trend_last_limits_rows():
    trend = _make_trend()
    output = _format_trend(trend, last=1)
    assert "2024-01-10" not in output
    assert "2024-01-11" in output


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(config="cronwatch.yml", job=None, granularity="daily", last=None)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_trends_all_jobs(capsys):
    trend = _make_trend()
    with patch("cronwatch.cli_trends.load_config") as mock_cfg, \
         patch("cronwatch.cli_trends.HistoryStore") as mock_store_cls, \
         patch("cronwatch.cli_trends.compute_all_trends", return_value=[trend]):
        mock_cfg.return_value = MagicMock(history_path="/tmp/h")
        run_trends(_make_args())
    captured = capsys.readouterr()
    assert "backup" in captured.out


def test_run_trends_single_job(capsys):
    trend = _make_trend("sync")
    with patch("cronwatch.cli_trends.load_config") as mock_cfg, \
         patch("cronwatch.cli_trends.HistoryStore") as mock_store_cls, \
         patch("cronwatch.cli_trends.compute_trend", return_value=trend):
        mock_cfg.return_value = MagicMock(history_path="/tmp/h")
        mock_store_cls.return_value.load.return_value = []
        run_trends(_make_args(job="sync"))
    captured = capsys.readouterr()
    assert "sync" in captured.out


def test_run_trends_exits_when_no_data(capsys):
    with patch("cronwatch.cli_trends.load_config") as mock_cfg, \
         patch("cronwatch.cli_trends.HistoryStore") as mock_store_cls, \
         patch("cronwatch.cli_trends.compute_trend", return_value=None):
        mock_cfg.return_value = MagicMock(history_path="/tmp/h")
        mock_store_cls.return_value.load.return_value = []
        with pytest.raises(SystemExit) as exc:
            run_trends(_make_args(job="missing"))
    assert exc.value.code == 1
