"""Integration entry-point: registers the 'checkpoints' sub-command into the
main cronwatch CLI.

Usage (from cli.py or a top-level entry-point script)::

    from cronwatch.cli_checkpoints_integration import register
    register(subparsers)
"""

from __future__ import annotations

import argparse

from cronwatch.cli_checkpoints import build_checkpoints_parser


def register(subparsers: argparse._SubParsersAction) -> None:
    """Attach the checkpoints sub-command to *subparsers*."""
    build_checkpoints_parser(subparsers)


def checkpoints_entry_point() -> None:
    """Standalone entry-point for the checkpoints command.

    Can be wired up in pyproject.toml::

        [project.scripts]
        cronwatch-checkpoints = "cronwatch.cli_checkpoints_integration:checkpoints_entry_point"
    """
    import sys

    parser = argparse.ArgumentParser(
        prog="cronwatch-checkpoints",
        description="Inspect mid-job progress checkpoints recorded by cronwatch.",
    )
    subparsers = parser.add_subparsers(dest="command")
    build_checkpoints_parser(subparsers)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)
