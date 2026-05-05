"""CLI sub-command for pruning cronwatch history."""

from __future__ import annotations

import argparse
import logging
import sys

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.pruner import prune_all_jobs

logger = logging.getLogger(__name__)


def build_prune_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    """Register the *prune* sub-command on *subparsers*."""
    parser = subparsers.add_parser(
        "prune",
        help="Remove old job-run records from history.",
    )
    parser.add_argument(
        "-c", "--config",
        default="cronwatch.yml",
        help="Path to the cronwatch config file (default: cronwatch.yml).",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        metavar="DAYS",
        help="Remove runs older than DAYS days.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        metavar="N",
        help="Keep only the N most-recent runs per job.",
    )
    parser.add_argument(
        "--job",
        dest="jobs",
        action="append",
        metavar="JOB_NAME",
        help="Limit pruning to specific job(s). May be repeated.",
    )
    return parser


def run_prune(args: argparse.Namespace) -> None:
    """Execute the prune sub-command."""
    if args.max_age_days is None and args.max_runs is None:
        logger.error("Specify at least one of --max-age-days or --max-runs.")
        sys.exit(1)

    config = load_config(args.config)
    store = HistoryStore(config.history_path)

    job_names: list[str] = args.jobs if args.jobs else [j.name for j in config.jobs]

    totals = prune_all_jobs(
        store,
        job_names,
        max_age_days=args.max_age_days,
        max_runs=args.max_runs,
    )

    grand_total = sum(totals.values())
    print(f"Pruned {grand_total} record(s) across {len(totals)} job(s).")
    for name, count in totals.items():
        if count:
            print(f"  {name}: {count} removed")
