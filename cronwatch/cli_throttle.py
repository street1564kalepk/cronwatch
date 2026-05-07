"""CLI subcommand for managing alert throttle state."""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.throttle import ThrottleStore

_DEFAULT_THROTTLE_PATH = "/var/lib/cronwatch/throttle.json"


def build_throttle_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "throttle",
        help="Inspect or clear alert throttle state",
    )
    sub = parser.add_subparsers(dest="throttle_cmd", required=True)

    show_p = sub.add_parser("show", help="Show currently throttled alerts")
    show_p.add_argument("--job", metavar="NAME", help="Filter by job name")

    clear_p = sub.add_parser("clear", help="Clear throttle entries")
    clear_p.add_argument("--job", metavar="NAME", help="Clear only entries for this job")

    for p in (show_p, clear_p):
        p.add_argument(
            "--throttle-file",
            default=_DEFAULT_THROTTLE_PATH,
            metavar="PATH",
            help="Path to throttle state file (default: %(default)s)",
        )

    parser.set_defaults(func=run_throttle)


def run_throttle(args: argparse.Namespace) -> None:
    store = ThrottleStore(path=args.throttle_file)
    store.load()

    if args.throttle_cmd == "show":
        entries = list(store._entries.values())
        if args.job:
            entries = [e for e in entries if e.job_name == args.job]
        if not entries:
            print("No throttled alerts.")
            return
        print(f"{'JOB':<30} {'TYPE':<15} {'LAST SENT (UTC)':<30}")
        print("-" * 75)
        for e in sorted(entries, key=lambda x: x.last_sent, reverse=True):
            print(f"{e.job_name:<30} {e.alert_type:<15} {e.last_sent.isoformat():<30}")
            throttled = store.is_throttled(e.job_name, e.alert_type)
            status = "[throttled]" if throttled else "[expired]"
            print(f"  {status}")

    elif args.throttle_cmd == "clear":
        job = getattr(args, "job", None)
        count = store.clear(job_name=job)
        target = f"job '{job}'" if job else "all jobs"
        print(f"Cleared {count} throttle entr{'y' if count == 1 else 'ies'} for {target}.")
