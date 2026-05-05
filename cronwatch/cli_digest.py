"""CLI entry-point for sending a cronwatch digest on demand."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta

from cronwatch.config import load_config
from cronwatch.digest import send_digest
from cronwatch.history import HistoryStore

logger = logging.getLogger(__name__)


def build_digest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch-digest",
        description="Send a digest email summarising recent cron job activity.",
    )
    parser.add_argument(
        "--config",
        default="cronwatch.yml",
        help="Path to cronwatch config file (default: cronwatch.yml)",
    )
    parser.add_argument(
        "--history-dir",
        default=".cronwatch_history",
        dest="history_dir",
        help="Directory containing job history files.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to include in the digest (default: 24).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the digest body instead of emailing it.",
    )
    return parser


def run_digest(argv: list[str] | None = None) -> int:
    """Parse args, load config, and dispatch (or print) the digest."""
    parser = build_digest_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    cfg = load_config(args.config)
    store = HistoryStore(args.history_dir)
    since = datetime.utcnow() - timedelta(hours=args.hours)

    if args.dry_run:
        from cronwatch.digest import collect_digest_data
        from cronwatch.report import format_report

        job_names = [j.name for j in cfg.jobs]
        summaries = collect_digest_data(store, job_names, since)
        print(format_report(summaries))
        return 0

    ok = send_digest(cfg, store, cfg.alert, since=since)
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_digest())
