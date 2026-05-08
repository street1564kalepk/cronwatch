"""CLI sub-command for inspecting job checkpoints."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.checkpoints import CheckpointStore


def build_checkpoints_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "checkpoints",
        help="Inspect mid-job progress checkpoints.",
    )
    parser.add_argument("run_id", help="Run ID to inspect.")
    parser.add_argument(
        "--store",
        default=".cronwatch/checkpoints.json",
        metavar="FILE",
        help="Path to checkpoint store (default: .cronwatch/checkpoints.json).",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Remove all checkpoints for the given run ID after displaying them.",
    )
    parser.set_defaults(func=run_checkpoints)


def run_checkpoints(args: argparse.Namespace) -> None:
    store = CheckpointStore(Path(args.store))
    checkpoints = store.get(args.run_id)

    if not checkpoints:
        print(f"No checkpoints found for run {args.run_id}.")
        sys.exit(0)

    print(f"Checkpoints for run {args.run_id} ({len(checkpoints)} total):")
    print(f"  {'#':<4} {'Label':<30} {'Recorded At':<28} Metadata")
    print("  " + "-" * 80)
    for idx, cp in enumerate(checkpoints, start=1):
        meta = ", ".join(f"{k}={v}" for k, v in cp.metadata.items()) if cp.metadata else ""
        print(f"  {idx:<4} {cp.label:<30} {cp.recorded_at.isoformat():<28} {meta}")

    if args.clear:
        store.clear(args.run_id)
        print(f"\nCleared checkpoints for run {args.run_id}.")
