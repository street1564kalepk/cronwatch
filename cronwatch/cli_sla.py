"""CLI sub-command: ``cronwatch sla`` – display SLA status for monitored jobs."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.sla import SLAPolicy, check_all_slas


def build_sla_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("sla", help="Check SLA compliance for cron jobs")
    p.add_argument("--config", default="cronwatch.yml", help="Path to config file")
    p.add_argument("--history-dir", default=".cronwatch", help="History data directory")
    p.add_argument("--window-days", type=int, default=7, help="Lookback window in days")
    p.add_argument(
        "--max-failure-rate",
        type=float,
        default=0.1,
        help="Maximum allowed failure rate (0.0–1.0, default 0.10)",
    )
    p.add_argument(
        "--max-avg-duration",
        type=float,
        default=3600.0,
        help="Maximum allowed average duration in seconds (default 3600)",
    )
    p.add_argument("--job", dest="job_filter", default=None, help="Limit to a single job")
    p.set_defaults(func=run_sla)


def run_sla(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    store = HistoryStore(args.history_dir)

    job_names = (
        [args.job_filter]
        if args.job_filter
        else [j.name for j in cfg.jobs]
    )

    policies: List[SLAPolicy] = [
        SLAPolicy(
            job_name=name,
            max_failure_rate=args.max_failure_rate,
            max_avg_duration_seconds=args.max_avg_duration,
            window_days=args.window_days,
        )
        for name in job_names
    ]

    results = check_all_slas(policies, store)
    any_violation = False

    for job_name, violations in results.items():
        if violations:
            any_violation = True
            for v in violations:
                print(f"VIOLATION  {v.summary()}")
        else:
            print(f"OK         [{job_name}] within SLA")

    if any_violation:
        sys.exit(1)
