"""CLI sub-commands for snapshot management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwatch.history import HistoryStore
from cronwatch.snapshots import diff_snapshots, load_snapshot, save_snapshot, take_snapshot


def build_snapshot_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("snapshot", help="Manage job-status snapshots")
    sub = p.add_subparsers(dest="snapshot_cmd", required=True)

    take_p = sub.add_parser("take", help="Capture a new snapshot")
    take_p.add_argument("--history", default="/var/lib/cronwatch/history.json", metavar="FILE")
    take_p.add_argument("--output", required=True, metavar="FILE", help="Where to write snapshot")

    diff_p = sub.add_parser("diff", help="Compare two snapshots")
    diff_p.add_argument("before", metavar="BEFORE", help="Older snapshot file")
    diff_p.add_argument("after", metavar="AFTER", help="Newer snapshot file")
    diff_p.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")

    show_p = sub.add_parser("show", help="Display a snapshot")
    show_p.add_argument("file", metavar="FILE")
    show_p.add_argument("--json", dest="as_json", action="store_true")


def run_snapshot(args: argparse.Namespace) -> None:
    if args.snapshot_cmd == "take":
        store = HistoryStore(Path(args.history))
        store.load()
        snap = take_snapshot(store)
        save_snapshot(snap, Path(args.output))
        print(f"Snapshot written to {args.output} ({len(snap.jobs)} jobs)")

    elif args.snapshot_cmd == "diff":
        before = load_snapshot(Path(args.before))
        after = load_snapshot(Path(args.after))
        if before is None:
            print(f"ERROR: cannot load snapshot: {args.before}", file=sys.stderr)
            sys.exit(1)
        if after is None:
            print(f"ERROR: cannot load snapshot: {args.after}", file=sys.stderr)
            sys.exit(1)
        diff = diff_snapshots(before, after)
        if args.as_json:
            print(json.dumps(diff, indent=2))
        else:
            if not diff:
                print("No changes between snapshots.")
            else:
                for name, info in diff.items():
                    print(f"{name}: {info['status']}")
                    if info["status"] == "changed":
                        for field, vals in info["changes"].items():
                            print(f"  {field}: {vals['before']} -> {vals['after']}")

    elif args.snapshot_cmd == "show":
        snap = load_snapshot(Path(args.file))
        if snap is None:
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            from dataclasses import asdict
            print(json.dumps(asdict(snap), indent=2))
        else:
            print(f"Snapshot taken at: {snap.taken_at}")
            for j in snap.jobs:
                rate = f"{j.success_count}/{j.total_runs}" if j.total_runs else "no runs"
                print(f"  {j.job_name}: {rate} ok, last_exit={j.last_exit_code}")
