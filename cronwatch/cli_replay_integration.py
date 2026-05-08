"""Integration helper: register the replay sub-command in the main CLI.

This module is imported by cronwatch/cli.py to wire up the 'replay'
sub-command alongside other cronwatch commands.

Usage (inside cli.py main):
    from cronwatch.cli_replay_integration import register
    register(subparsers)
"""

from __future__ import annotations

import argparse
import logging

from cronwatch.cli_replay import build_replay_parser

log = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Attach the replay command to *subparsers*."""
    build_replay_parser(subparsers)
    log.debug("replay sub-command registered")


def replay_entry_point() -> None:
    """Standalone entry point for `cronwatch-replay` console script."""
    import sys
    from cronwatch.cli import setup_logging

    parser = argparse.ArgumentParser(
        prog="cronwatch-replay",
        description="Re-run failed cron jobs from history",
    )
    sub = parser.add_subparsers(dest="command")
    build_replay_parser(sub)

    args = parser.parse_args()
    setup_logging(getattr(args, "verbose", False))

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)
