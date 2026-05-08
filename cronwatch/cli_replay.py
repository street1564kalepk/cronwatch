"""CLI sub-command: cronwatch replay"""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.replay import find_failed_runs, replay_all_failures


def build_replay_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "replay",
        help="Re-run failed cron jobs from history",
    )
    p.add_argument("job", help="Job name to replay")
    p.add_argument(
        "--command",
        required=True,
        help="Shell command to execute for the replay",
    )
    p.add_argument(
        "--config",
        default="cronwatch.yaml",
        help="Path to config file",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds for each replay attempt",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List failed runs without executing them",
    )
    p.set_defaults(func=run_replay)


def run_replay(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    store = HistoryStore(cfg.history_path)

    if args.dry_run:
        failed = find_failed_runs(store, args.job)
        if not failed:
            print(f"No failed runs found for '{args.job}'.")
            return
        print(f"Failed runs for '{args.job}':")
        for r in failed:
            print(f"  {r.run_id}  started={r.started_at}")
        return

    results = replay_all_failures(
        store, args.job, args.command, timeout=args.timeout
    )
    if not results:
        print(f"Nothing to replay for '{args.job}'.")
        return

    ok = sum(1 for r in results if r.succeeded)
    fail = len(results) - ok
    print(f"Replayed {len(results)} run(s): {ok} succeeded, {fail} failed.")
    for r in results:
        status = "OK" if r.succeeded else f"FAIL(rc={r.returncode})"
        print(f"  [{status}] original={r.original_run_id} at={r.replayed_at.isoformat()}")
        if not r.succeeded and r.stderr:
            print(f"    stderr: {r.stderr[:120]}")

    if fail:
        sys.exit(1)
