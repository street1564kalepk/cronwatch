"""Tests for cronwatch.cli_sla."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_sla import build_sla_parser, run_sla
from cronwatch.sla import SLAViolation
from datetime import datetime


@pytest.fixture()
def subparsers():
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


def test_build_sla_parser_registers_command(subparsers):
    build_sla_parser(subparsers)
    assert "sla" in subparsers.choices


def _make_args(**kwargs):
    defaults = dict(
        config="cronwatch.yml",
        history_dir=".cronwatch",
        window_days=7,
        max_failure_rate=0.1,
        max_avg_duration=3600.0,
        job_filter=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_config(*job_names):
    cfg = MagicMock()
    cfg.jobs = [MagicMock(name=n) for n in job_names]
    for j, n in zip(cfg.jobs, job_names):
        j.name = n
    return cfg


def test_run_sla_prints_ok_when_no_violations(capsys):
    with (
        patch("cronwatch.cli_sla.load_config", return_value=_make_config("backup")),
        patch("cronwatch.cli_sla.HistoryStore"),
        patch("cronwatch.cli_sla.check_all_slas", return_value={"backup": []}),
    ):
        run_sla(_make_args())
    out = capsys.readouterr().out
    assert "OK" in out
    assert "backup" in out


def test_run_sla_exits_nonzero_on_violation(capsys):
    violation = SLAViolation(
        job_name="backup",
        reason="failure_rate",
        actual=0.5,
        threshold=0.1,
        checked_at=datetime.utcnow(),
    )
    with (
        patch("cronwatch.cli_sla.load_config", return_value=_make_config("backup")),
        patch("cronwatch.cli_sla.HistoryStore"),
        patch("cronwatch.cli_sla.check_all_slas", return_value={"backup": [violation]}),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_sla(_make_args())
    assert exc_info.value.code == 1


def test_run_sla_respects_job_filter(capsys):
    with (
        patch("cronwatch.cli_sla.load_config", return_value=_make_config("backup", "sync")),
        patch("cronwatch.cli_sla.HistoryStore"),
        patch("cronwatch.cli_sla.check_all_slas", return_value={"sync": []}) as mock_check,
    ):
        run_sla(_make_args(job_filter="sync"))
    called_policies = mock_check.call_args[0][0]
    assert len(called_policies) == 1
    assert called_policies[0].job_name == "sync"
