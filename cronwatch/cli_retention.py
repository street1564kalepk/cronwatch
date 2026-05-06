"""CLI sub-command: cronwatch retention — apply retention policies."""

from __future__ import annotations

import argparse
import logging
import sys

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.retention import RetentionPolicy, apply_retention, retention_summary

logger = logging.getLogger(__name__)


def build_retention_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "retention",
        help="Apply retention policies to stored job history.",
    )
    parser.add_argument("--config", default="cronwatch.yaml", help="Path to config file.")
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
        help="Keep only the N most recent runs per job.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without making changes.")
    return parser


def run_retention(args: argparse.Namespace) -> None:
    if args.max_age_days is None and args.max_runs is None:
        print("Error: specify --max-age-days and/or --max-runs.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(args.config)
    store = HistoryStore(cfg.history_path)
    policy = RetentionPolicy(
        max_age_days=args.max_age_days,
        max_runs_per_job=args.max_runs,
    )

    if args.dry_run:
        # Load data without modifying; compute what *would* be removed.
        from cronwatch.pruner import prune_by_age, prune_by_count
        import copy

        data = store.load()
        preview: dict[str, int] = {}
        for job_name, runs in data.items():
            eff = policy.effective_for(job_name)
            tmp = list(runs)
            before = len(tmp)
            if eff.max_age_days is not None:
                tmp = prune_by_age(tmp, eff.max_age_days)
            if eff.max_runs_per_job is not None:
                tmp = prune_by_count(tmp, eff.max_runs_per_job)
            preview[job_name] = before - len(tmp)
        print("[DRY RUN] " + retention_summary(preview))
        return

    removed = apply_retention(store, policy)
    print(retention_summary(removed))
