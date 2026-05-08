"""CLI sub-command for inspecting escalation state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.escalation import EscalationStore


def build_escalation_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "escalation",
        help="Show or reset alert escalation state for cron jobs.",
    )
    p.add_argument(
        "--state-file",
        default=".cronwatch/escalation.json",
        help="Path to escalation state file (default: .cronwatch/escalation.json).",
    )
    sub = p.add_subparsers(dest="escalation_cmd")

    show = sub.add_parser("show", help="Show escalation state for all or one job.")
    show.add_argument("--job", default=None, help="Filter to a specific job name.")

    reset = sub.add_parser("reset", help="Reset escalation state for a job.")
    reset.add_argument("job", help="Job name to reset.")

    p.set_defaults(func=run_escalation)


def run_escalation(args: argparse.Namespace) -> None:
    store = EscalationStore(Path(args.state_file))

    cmd = getattr(args, "escalation_cmd", None)

    if cmd == "reset":
        store.record_success(args.job)
        print(f"Escalation state reset for job '{args.job}'.")
        return

    # default: show
    states = store._states
    if not states:
        print("No escalation state recorded.")
        return

    job_filter = getattr(args, "job", None)
    rows = [
        s for s in states.values()
        if job_filter is None or s.job_name == job_filter
    ]

    if not rows:
        print(f"No escalation state found for job '{job_filter}'.")
        sys.exit(1)

    header = f"{'JOB':<30} {'FAILURES':>8} {'ESCALATED':>10}"
    print(header)
    print("-" * len(header))
    for s in sorted(rows, key=lambda x: x.job_name):
        print(f"{s.job_name:<30} {s.consecutive_failures:>8} {str(s.escalated):>10}")
