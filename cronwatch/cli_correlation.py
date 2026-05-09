"""CLI sub-command: cronwatch correlation — show root-cause analysis for failures."""
from __future__ import annotations

import argparse
from datetime import timedelta

from cronwatch.correlation import correlate_all, correlate_failure
from cronwatch.dependencies import DependencyGraph
from cronwatch.history import HistoryStore


def build_correlation_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "correlation",
        help="Correlate job failures with upstream dependency failures.",
    )
    p.add_argument("--history", default="cronwatch_history.json",
                   help="Path to history file.")
    p.add_argument("--deps", default="cronwatch_deps.json",
                   help="Path to dependency graph file.")
    p.add_argument("--job", default=None,
                   help="Analyse a single job (default: all jobs with recent failures).")
    p.add_argument("--window", type=int, default=60,
                   help="Look-back window in minutes (default: 60).")
    p.set_defaults(func=run_correlation)


def run_correlation(args: argparse.Namespace) -> None:
    store = HistoryStore(args.history)
    graph = DependencyGraph(args.deps)
    window = timedelta(minutes=args.window)

    if args.job:
        results = {args.job: correlate_failure(args.job, store, graph, window)}
    else:
        results = correlate_all(store, graph, window)

    if not results:
        print("No recent failures found.")
        return

    header = f"{'Job':<30} {'Root Cause':<30} {'Confidence':>10}  Upstream Failures"
    print(header)
    print("-" * len(header))
    for name, res in sorted(results.items()):
        root = res.likely_root_cause or "(unknown)"
        ups = ", ".join(res.upstream_failures) if res.upstream_failures else "—"
        conf = f"{res.confidence:.0%}"
        print(f"{name:<30} {root:<30} {conf:>10}  {ups}")
