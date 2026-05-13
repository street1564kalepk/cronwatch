"""CLI sub-command for managing the job quarantine list."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cronwatch.quarantine import QuarantineStore

_DEFAULT_PATH = Path("~/.cronwatch/quarantine.json")


def build_quarantine_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("quarantine", help="Manage job quarantine list")
    p.add_argument("--store", type=Path, default=_DEFAULT_PATH, help="Path to quarantine store")
    sub = p.add_subparsers(dest="quarantine_cmd", required=True)

    add_p = sub.add_parser("add", help="Quarantine a job")
    add_p.add_argument("job", help="Job name")
    add_p.add_argument("--reason", default="manual", help="Reason for quarantine")

    rel_p = sub.add_parser("release", help="Release a job from quarantine")
    rel_p.add_argument("job", help="Job name")

    sub.add_parser("list", help="List quarantined jobs")

    p.set_defaults(func=run_quarantine)


def run_quarantine(args: argparse.Namespace) -> None:
    store_path = Path(args.store).expanduser()
    store = QuarantineStore(store_path)

    if args.quarantine_cmd == "add":
        entry = store.quarantine(args.job, args.reason, now=datetime.now(timezone.utc))
        print(f"Quarantined '{entry.job_name}' at {entry.quarantined_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Reason: {entry.reason}")

    elif args.quarantine_cmd == "release":
        released = store.release(args.job, now=datetime.now(timezone.utc))
        if released:
            print(f"Released '{args.job}' from quarantine.")
        else:
            print(f"Job '{args.job}' is not currently quarantined.", file=sys.stderr)
            sys.exit(1)

    elif args.quarantine_cmd == "list":
        active = store.active_entries()
        if not active:
            print("No jobs currently quarantined.")
            return
        header = f"{'Job':<30}  {'Quarantined At':<22}  Reason"
        print(header)
        print("-" * len(header))
        for entry in sorted(active, key=lambda e: e.quarantined_at):
            ts = entry.quarantined_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{entry.job_name:<30}  {ts:<22}  {entry.reason}")
