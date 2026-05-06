"""CLI sub-command: cronwatch tags — list tags and their associated jobs."""

from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.tags import build_tag_index


def build_tags_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "tags",
        help="List tags and the jobs associated with them.",
    )
    parser.add_argument(
        "--config",
        default="cronwatch.yaml",
        help="Path to cronwatch config file (default: cronwatch.yaml).",
    )
    parser.add_argument(
        "--tag",
        metavar="TAG",
        help="Show only jobs for this specific tag.",
    )
    parser.set_defaults(func=run_tags)


def run_tags(args: argparse.Namespace) -> None:
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    index = build_tag_index(config.jobs)

    if args.tag:
        jobs = index.jobs_for_tag(args.tag)
        if not jobs:
            print(f"No jobs found for tag '{args.tag}'.")
        else:
            print(f"Tag '{args.tag}':")
            for job in sorted(jobs):
                print(f"  - {job}")
        return

    tags = index.all_tags()
    if not tags:
        print("No tags defined.")
        return

    for tag in tags:
        jobs = index.jobs_for_tag(tag)
        print(f"{tag}: {', '.join(sorted(jobs))}")
