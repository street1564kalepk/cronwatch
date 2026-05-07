"""CLI sub-command: cronwatch metrics — display job runtime metrics."""
from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.metrics import collect_metrics, format_metrics


def build_metrics_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "metrics",
        help="Display runtime metrics for monitored cron jobs.",
    )
    parser.add_argument(
        "--config",
        default="cronwatch.yml",
        help="Path to cronwatch config file (default: cronwatch.yml).",
    )
    parser.add_argument(
        "--history",
        default="cronwatch_history.json",
        help="Path to history file (default: cronwatch_history.json).",
    )
    parser.add_argument(
        "--job",
        metavar="JOB_NAME",
        help="Filter metrics to a single job.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output metrics as JSON.",
    )
    parser.set_defaults(func=run_metrics)


def run_metrics(args: argparse.Namespace) -> None:
    store = HistoryStore(path=args.history)
    store.load()

    all_metrics = collect_metrics(store)

    if args.job:
        if args.job not in all_metrics:
            print(f"No metrics found for job: {args.job}", file=sys.stderr)
            sys.exit(1)
        all_metrics = {args.job: all_metrics[args.job]}

    if args.json:
        import json
        import dataclasses
        print(json.dumps(
            {k: dataclasses.asdict(v) for k, v in all_metrics.items()},
            indent=2,
        ))
    else:
        print(format_metrics(all_metrics))
