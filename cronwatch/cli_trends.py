"""CLI sub-command: cronwatch trends — show duration/success-rate trends."""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.trends import compute_all_trends, compute_trend, JobTrend


def build_trends_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("trends", help="Show job execution trends")
    p.add_argument("--config", default="cronwatch.yml", help="Config file path")
    p.add_argument("--job", default=None, help="Limit output to a single job")
    p.add_argument(
        "--granularity",
        choices=["daily", "weekly"],
        default="daily",
        help="Bucket size for trend analysis (default: daily)",
    )
    p.add_argument(
        "--last",
        type=int,
        default=None,
        metavar="N",
        help="Show only the last N buckets",
    )
    p.set_defaults(func=run_trends)


def _format_trend(trend: JobTrend, last: int | None) -> str:
    lines = [
        f"Job: {trend.job_name}  [{trend.granularity}]",
        f"  {'Bucket':<14}  {'Runs':>5}  {'Avg dur (s)':>12}  {'Success %':>10}  Status",
        "  " + "-" * 58,
    ]
    points = trend.points[-last:] if last else trend.points
    for pt in points:
        status = "▲" if trend.improving else ("▼" if trend.degrading else "─")
        lines.append(
            f"  {pt.bucket:<14}  {pt.run_count:>5}  "
            f"{pt.avg_duration:>12.1f}  {pt.success_rate * 100:>9.1f}%  {status}"
        )
    return "\n".join(lines)


def run_trends(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    store = HistoryStore(cfg.history_path)

    if args.job:
        runs = store.load(args.job)
        trend = compute_trend(args.job, runs, args.granularity)
        if trend is None:
            print(f"No finished runs found for job '{args.job}'.", file=sys.stderr)
            sys.exit(1)
        trends = [trend]
    else:
        trends = compute_all_trends(store, args.granularity)
        if not trends:
            print("No trend data available.", file=sys.stderr)
            sys.exit(0)

    for trend in trends:
        print(_format_trend(trend, args.last))
        print()
