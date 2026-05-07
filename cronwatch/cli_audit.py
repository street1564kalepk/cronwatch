"""CLI sub-command for viewing the cronwatch audit log."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.audit import AuditStore, filter_events


def build_audit_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("audit", help="View the cronwatch audit log")
    p.add_argument(
        "--log",
        default="/var/lib/cronwatch/audit.log",
        help="Path to audit log file (default: %(default)s)",
    )
    p.add_argument("--event-type", metavar="TYPE", help="Filter by event type")
    p.add_argument("--job", metavar="JOB", help="Filter by job name")
    p.add_argument(
        "--tail",
        type=int,
        default=0,
        metavar="N",
        help="Show only the last N events (0 = all)",
    )
    p.set_defaults(func=run_audit)


def run_audit(args: argparse.Namespace) -> None:
    store = AuditStore(Path(args.log))
    events = store.load()

    if not events:
        print("No audit events found.")
        return

    filtered = filter_events(
        events,
        event_type=getattr(args, "event_type", None),
        job_name=getattr(args, "job", None),
    )

    if not filtered:
        print("No events match the given filters.")
        return

    if args.tail > 0:
        filtered = filtered[-args.tail :]

    col_ts = max(len(e.timestamp) for e in filtered)
    col_type = max(len(e.event_type) for e in filtered)
    col_job = max((len(e.job_name or "-") for e in filtered), default=3)

    header = (
        f"{'TIMESTAMP':<{col_ts}}  "
        f"{'EVENT':<{col_type}}  "
        f"{'JOB':<{col_job}}  DETAIL"
    )
    print(header)
    print("-" * len(header))

    for e in filtered:
        job_col = (e.job_name or "-")
        print(
            f"{e.timestamp:<{col_ts}}  "
            f"{e.event_type:<{col_type}}  "
            f"{job_col:<{col_job}}  {e.detail}"
        )
