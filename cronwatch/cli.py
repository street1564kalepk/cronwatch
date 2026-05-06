"""Main CLI entry-point for cronwatch."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution times and send alerts.",
    )
    parser.add_argument(
        "--config", default="/etc/cronwatch/config.yaml", metavar="FILE",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    subparsers = parser.add_subparsers(dest="command")

    from cronwatch.cli_report import build_report_parser
    build_report_parser(subparsers)

    from cronwatch.cli_digest import build_digest_parser
    build_digest_parser(subparsers)

    from cronwatch.cli_prune import build_prune_parser
    build_prune_parser(subparsers)

    from cronwatch.cli_retention import build_retention_parser
    build_retention_parser(subparsers)

    from cronwatch.cli_baseline import build_baseline_parser
    build_baseline_parser(subparsers)

    from cronwatch.cli_tags import build_tags_parser
    build_tags_parser(subparsers)

    from cronwatch.cli_snapshot import build_snapshot_parser
    build_snapshot_parser(subparsers)

    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "report":
        from cronwatch.cli_report import run_report
        run_report(args)
    elif args.command == "digest":
        from cronwatch.cli_digest import run_digest
        run_digest(args)
    elif args.command == "prune":
        from cronwatch.cli_prune import run_prune
        run_prune(args)
    elif args.command == "retention":
        from cronwatch.cli_retention import run_retention
        run_retention(args)
    elif args.command == "baseline":
        from cronwatch.cli_baseline import run_baseline
        run_baseline(args)
    elif args.command == "tags":
        from cronwatch.cli_tags import run_tags
        run_tags(args)
    elif args.command == "snapshot":
        from cronwatch.cli_snapshot import run_snapshot
        run_snapshot(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
