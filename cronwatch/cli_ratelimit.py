"""CLI sub-command for inspecting and resetting rate-limit state."""

from __future__ import annotations

import argparse
import sys

from cronwatch.ratelimit import RateLimitStore


def build_ratelimit_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "ratelimit",
        help="Inspect or reset alert rate-limit state",
    )
    p.add_argument(
        "--state-file",
        default=".cronwatch_ratelimit.json",
        metavar="PATH",
        help="Path to the rate-limit state file (default: %(default)s)",
    )
    sub = p.add_subparsers(dest="rl_cmd")

    # show
    sub.add_parser("show", help="List current rate-limit entries")

    # reset
    reset_p = sub.add_parser("reset", help="Reset rate-limit counter for a job/type pair")
    reset_p.add_argument("job", help="Job name")
    reset_p.add_argument(
        "--type",
        dest="alert_type",
        default="failure",
        help="Alert type (default: %(default)s)",
    )

    p.set_defaults(func=run_ratelimit)


def run_ratelimit(args: argparse.Namespace) -> None:
    store = RateLimitStore(args.state_file)

    if args.rl_cmd == "reset":
        store.reset(args.job, args.alert_type)
        print(f"Rate-limit counter reset for {args.job}/{args.alert_type}.")
        return

    # default: show
    entries = store.all_entries()
    if not entries:
        print("No rate-limit entries found.")
        return

    header = f"{'JOB':<30} {'TYPE':<12} {'COUNT':>6}  {'WINDOW START'}"
    print(header)
    print("-" * len(header))
    for e in sorted(entries, key=lambda x: (x.job_name, x.alert_type)):
        ws = e.window_start.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"{e.job_name:<30} {e.alert_type:<12} {e.count:>6}  {ws}")
