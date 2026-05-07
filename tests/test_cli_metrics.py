"""Tests for cronwatch/cli_metrics.py"""
from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_metrics import build_metrics_parser, run_metrics
from cronwatch.metrics import JobMetrics


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_metrics_parser_registers_command(subparsers):
    build_metrics_parser(subparsers)
    assert "metrics" in subparsers.choices


def _make_args(**kwargs):
    defaults = {
        "config": "cronwatch.yml",
        "history": "cronwatch_history.json",
        "job": None,
        "json": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_metrics():
    return {
        "backup": JobMetrics(
            job_name="backup",
            total_runs=3,
            successful_runs=3,
            failed_runs=0,
            avg_duration_seconds=10.0,
            max_duration_seconds=15.0,
            min_duration_seconds=5.0,
            last_status="success",
        )
    }


def test_run_metrics_prints_table(capsys):
    with patch("cronwatch.cli_metrics.HistoryStore") as MockStore, \
         patch("cronwatch.cli_metrics.collect_metrics", return_value=_make_metrics()):
        instance = MockStore.return_value
        run_metrics(_make_args())
        output = capsys.readouterr().out
        assert "backup" in output


def test_run_metrics_json_output(capsys):
    with patch("cronwatch.cli_metrics.HistoryStore"), \
         patch("cronwatch.cli_metrics.collect_metrics", return_value=_make_metrics()):
        run_metrics(_make_args(json=True))
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "backup" in data
        assert data["backup"]["total_runs"] == 3


def test_run_metrics_job_filter(capsys):
    metrics = _make_metrics()
    metrics["other"] = JobMetrics(job_name="other", total_runs=1)
    with patch("cronwatch.cli_metrics.HistoryStore"), \
         patch("cronwatch.cli_metrics.collect_metrics", return_value=metrics):
        run_metrics(_make_args(job="backup"))
        output = capsys.readouterr().out
        assert "backup" in output
        assert "other" not in output


def test_run_metrics_unknown_job_exits(capsys):
    with patch("cronwatch.cli_metrics.HistoryStore"), \
         patch("cronwatch.cli_metrics.collect_metrics", return_value=_make_metrics()):
        with pytest.raises(SystemExit) as exc:
            run_metrics(_make_args(job="nonexistent"))
        assert exc.value.code == 1
