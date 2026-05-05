"""CLI sub-command for displaying job history reports."""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.report import all_jobs_summary, job_summary, format_report

logger = logging.getLogger(__name__)


def build_report_parser(subparsers) -> argparse.ArgumentParser:
    p = subparsers.add_parser("report", help="Show job run history and statistics")
    p.add_argument("--job", metavar="NAME", help="Limit report to a specific job")
    p.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help="Only include runs from the last N days",
    )
    p.add_argument(
        "--history-file",
        default="/var/lib/cronwatch/history.json",
        metavar="PATH",
        help="Path to history JSON file",
    )
    p.add_argument("--config", default="/etc/cronwatch/config.yaml", metavar="PATH")
    return p


def run_report(args: argparse.Namespace) -> int:
    since: Optional[datetime] = None
    if args.days is not None:
        since = datetime.utcnow() - timedelta(days=args.days)

    store = HistoryStore(args.history_file)

    if args.job:
        summaries = [job_summary(store, args.job, since=since)]
    else:
        summaries = all_jobs_summary(store, since=since)

    print(format_report(summaries))
    return 0


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(prog="cronwatch-report")
    subs = parser.add_subparsers(dest="command")
    build_report_parser(subs)
    parsed = parser.parse_args()
    sys.exit(run_report(parsed))
