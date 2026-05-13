"""CLI sub-command for inspecting and resetting circuit breakers."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatch.circuit_breaker import (
    CircuitBreakerStore,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_HALF_OPEN,
    record_success,
)

_DEFAULT_PATH = Path("cronwatch_circuit_breakers.json")


def build_circuit_breaker_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("circuit-breaker", help="Inspect or reset circuit breakers")
    p.add_argument("--data-file", default=str(_DEFAULT_PATH), help="Path to circuit breaker state file")
    sub = p.add_subparsers(dest="cb_action", required=True)

    sub.add_parser("show", help="Show all circuit breaker states")

    reset_p = sub.add_parser("reset", help="Manually reset (close) a circuit breaker")
    reset_p.add_argument("job", help="Job name to reset")


def _state_label(state: str) -> str:
    return {
        STATE_CLOSED: "CLOSED  ",
        STATE_OPEN: "OPEN    ",
        STATE_HALF_OPEN: "HALF-OPEN",
    }.get(state, state)


def run_circuit_breaker(args: argparse.Namespace) -> None:
    store = CircuitBreakerStore(Path(args.data_file))

    if args.cb_action == "show":
        entries = store.all()
        if not entries:
            print("No circuit breaker data found.")
            return
        print(f"{'Job':<30} {'State':<10} {'Failures':>8}  {'Opened At'}")
        print("-" * 70)
        for s in sorted(entries, key=lambda e: e.job_name):
            opened = s.opened_at.strftime("%Y-%m-%d %H:%M UTC") if s.opened_at else "-"
            print(f"{s.job_name:<30} {_state_label(s.state):<10} {s.failure_count:>8}  {opened}")

    elif args.cb_action == "reset":
        state = record_success(store, args.job)
        print(f"Circuit breaker for '{args.job}' has been reset (state: {state.state}).")
