"""CLI sub-command: cronwatch budgets — show budget violations for recent runs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.budgets import check_all_budgets, load_budget_policies
from cronwatch.history import HistoryStore


def build_budgets_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("budgets", help="Check job runtime budgets")
    p.add_argument(
        "--budgets-file",
        default="budgets.json",
        help="Path to budget policy JSON file (default: budgets.json)",
    )
    p.add_argument(
        "--history-file",
        default="history.json",
        help="Path to run history file (default: history.json)",
    )
    p.add_argument(
        "--job",
        dest="job_filter",
        default=None,
        help="Limit check to a specific job name",
    )
    p.add_argument(
        "--exceeded-only",
        action="store_true",
        default=False,
        help="Only show runs that fully exceeded the budget (not warnings)",
    )
    p.set_defaults(func=run_budgets)


def run_budgets(args: argparse.Namespace) -> None:
    policies = load_budget_policies(Path(args.budgets_file))
    if not policies:
        print("No budget policies found.")
        sys.exit(0)

    store = HistoryStore(Path(args.history_file))
    all_runs = store.load()

    if args.job_filter:
        all_runs = [r for r in all_runs if r.job_name == args.job_filter]

    violations = check_all_budgets(all_runs, policies)

    if args.exceeded_only:
        violations = [v for v in violations if v.exceeded]

    if not violations:
        print("No budget violations found.")
        sys.exit(0)

    header = f"{'JOB':<25} {'RUN ID':<36} {'BUDGET(s)':>10} {'ACTUAL(s)':>10} {'%USED':>7} {'STATUS':<10}"
    print(header)
    print("-" * len(header))
    for v in violations:
        status = "EXCEEDED" if v.exceeded else "WARNING"
        print(
            f"{v.job_name:<25} {v.run_id:<36} {v.budget_seconds:>10.1f} "
            f"{v.actual_seconds:>10.1f} {v.percent_used * 100:>6.1f}% {status:<10}"
        )
