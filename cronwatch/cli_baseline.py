"""CLI sub-command: cronwatch baseline — show per-job duration baselines."""

from __future__ import annotations

import argparse
import sys

from cronwatch.baseline import compute_all_baselines
from cronwatch.config import load_config
from cronwatch.history import HistoryStore


def build_baseline_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "baseline",
        help="Display duration baseline statistics for monitored jobs.",
    )
    parser.add_argument(
        "-c", "--config", default="cronwatch.yaml", help="Path to config file."
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        metavar="N",
        help="Minimum successful runs required to compute a baseline (default: 5).",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=2.0,
        help="Standard-deviation multiplier for anomaly bounds (default: 2.0).",
    )
    parser.add_argument(
        "job",
        nargs="?",
        default=None,
        help="Limit output to a single job name.",
    )
    parser.set_defaults(func=run_baseline)


def run_baseline(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    store = HistoryStore(cfg.history_path)
    history = store.load_all()

    if args.job:
        if args.job not in history:
            print(f"No history found for job: {args.job}", file=sys.stderr)
            sys.exit(1)
        history = {args.job: history[args.job]}

    baselines = compute_all_baselines(history, min_samples=args.min_samples)

    if not baselines:
        print("Not enough data to compute baselines (need more successful runs).")
        return

    header = f"{'Job':<30} {'Samples':>7} {'Mean(s)':>9} {'Stddev(s)':>10} {'Low(s)':>9} {'High(s)':>9}"
    print(header)
    print("-" * len(header))
    for job_name, stats in sorted(baselines.items()):
        low, high = stats.expected_range(sigma=args.sigma)
        print(
            f"{job_name:<30} {stats.sample_count:>7} "
            f"{stats.mean_duration:>9.2f} {stats.stddev_duration:>10.2f} "
            f"{low:>9.2f} {high:>9.2f}"
        )
