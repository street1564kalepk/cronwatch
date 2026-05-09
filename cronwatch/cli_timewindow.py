"""CLI sub-command for managing time windows."""

from __future__ import annotations

import argparse
from datetime import time

from cronwatch.timewindow import TimeWindow, TimeWindowStore

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_days(days_str: str) -> list[int]:
    """Accept comma-separated day names or integers (0-6)."""
    result = []
    for token in days_str.split(","):
        token = token.strip().lower()
        if token in _DAY_NAMES:
            result.append(_DAY_NAMES.index(token))
        elif token.isdigit():
            result.append(int(token))
        else:
            raise argparse.ArgumentTypeError(f"Unknown day: {token!r}")
    return sorted(set(result))


def build_timewindow_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("timewindow", help="Manage alert time windows")
    sub = p.add_subparsers(dest="tw_action", required=True)

    # list
    sub.add_parser("list", help="List all time windows")

    # add
    add = sub.add_parser("add", help="Add or replace a time window")
    add.add_argument("name", help="Window name")
    add.add_argument("start", help="Start time HH:MM (inclusive)")
    add.add_argument("end", help="End time HH:MM (exclusive)")
    add.add_argument("--days", default="mon,tue,wed,thu,fri,sat,sun",
                     help="Comma-separated days (default: all)")

    # remove
    rm = sub.add_parser("remove", help="Remove a time window")
    rm.add_argument("name", help="Window name")

    # check
    chk = sub.add_parser("check", help="Check if a named window is currently active")
    chk.add_argument("name", help="Window name")

    p.set_defaults(func=run_timewindow)


def run_timewindow(args: argparse.Namespace) -> None:
    store = TimeWindowStore(getattr(args, "timewindow_file", "timewindows.json"))

    if args.tw_action == "list":
        windows = store.all()
        if not windows:
            print("No time windows defined.")
            return
        print(f"{'NAME':<20} {'START':<8} {'END':<8} DAYS")
        for w in windows:
            day_str = ",".join(_DAY_NAMES[d] for d in w.days)
            print(f"{w.name:<20} {w.start.strftime('%H:%M'):<8} {w.end.strftime('%H:%M'):<8} {day_str}")

    elif args.tw_action == "add":
        days = _parse_days(args.days)
        window = TimeWindow(
            name=args.name,
            start=time.fromisoformat(args.start),
            end=time.fromisoformat(args.end),
            days=days,
        )
        store.add(window)
        print(f"Time window '{args.name}' saved.")

    elif args.tw_action == "remove":
        removed = store.remove(args.name)
        if removed:
            print(f"Time window '{args.name}' removed.")
        else:
            print(f"No window named '{args.name}'.")

    elif args.tw_action == "check":
        window = store.get(args.name)
        if window is None:
            print(f"No window named '{args.name}'.")
            return
        active = window.is_active()
        status = "ACTIVE" if active else "inactive"
        print(f"Window '{args.name}' is currently {status}.")
