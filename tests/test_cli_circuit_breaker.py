"""Tests for cronwatch.cli_circuit_breaker."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.circuit_breaker import BreakerState, CircuitBreakerStore, STATE_OPEN, STATE_CLOSED
from cronwatch.cli_circuit_breaker import build_circuit_breaker_parser, run_circuit_breaker


@pytest.fixture
def subparsers() -> argparse._SubParsersAction:
    parser = argparse.ArgumentParser()
    return parser.add_subparsers(dest="command")


def test_build_circuit_breaker_parser_registers_command(subparsers):
    build_circuit_breaker_parser(subparsers)
    parser = subparsers.choices["circuit-breaker"]
    assert parser is not None


def _make_args(tmp_path: Path, action: str, job: str | None = None) -> argparse.Namespace:
    ns = argparse.Namespace(
        data_file=str(tmp_path / "breakers.json"),
        cb_action=action,
    )
    if job is not None:
        ns.job = job
    return ns


def test_run_show_empty(tmp_path: Path, capsys):
    args = _make_args(tmp_path, "show")
    run_circuit_breaker(args)
    out = capsys.readouterr().out
    assert "No circuit breaker data" in out


def test_run_show_lists_entries(tmp_path: Path, capsys):
    store = CircuitBreakerStore(tmp_path / "breakers.json")
    s = BreakerState(
        job_name="nightly_sync",
        state=STATE_OPEN,
        failure_count=5,
        opened_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    store.put(s)

    args = _make_args(tmp_path, "show")
    run_circuit_breaker(args)
    out = capsys.readouterr().out
    assert "nightly_sync" in out
    assert "OPEN" in out
    assert "5" in out


def test_run_reset_closes_breaker(tmp_path: Path, capsys):
    store = CircuitBreakerStore(tmp_path / "breakers.json")
    s = BreakerState(
        job_name="etl",
        state=STATE_OPEN,
        failure_count=3,
        opened_at=datetime.now(timezone.utc),
    )
    store.put(s)

    args = _make_args(tmp_path, "reset", job="etl")
    run_circuit_breaker(args)
    out = capsys.readouterr().out
    assert "reset" in out.lower()

    reloaded = CircuitBreakerStore(tmp_path / "breakers.json")
    assert reloaded.get("etl").state == STATE_CLOSED
