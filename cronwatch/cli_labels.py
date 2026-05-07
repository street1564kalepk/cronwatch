"""CLI sub-commands for label-based job filtering."""
from __future__ import annotations

import argparse
import sys

from cronwatch.config import load_config
from cronwatch.labels import build_label_index


def build_labels_parser(subparsers: argparse.Action) -> None:
    parser = subparsers.add_parser(
        "labels",
        help="Query jobs by label",
    )
    sub = parser.add_subparsers(dest="labels_cmd", required=True)

    # labels list
    sub.add_parser("list", help="List all known labels")

    # labels jobs <label> [<label> ...]
    jobs_p = sub.add_parser("jobs", help="List jobs carrying given label(s)")
    jobs_p.add_argument("label", nargs="+", help="Label name(s)")

    # labels show <job>
    show_p = sub.add_parser("show", help="Show labels attached to a job")
    show_p.add_argument("job", help="Job name")

    parser.set_defaults(func=run_labels)


def run_labels(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    index = build_label_index(config)

    if args.labels_cmd == "list":
        labels = index.all_labels()
        if not labels:
            print("No labels defined.")
        else:
            for lbl in labels:
                print(lbl)

    elif args.labels_cmd == "jobs":
        if len(args.label) == 1:
            jobs = index.jobs_for_label(args.label[0])
        else:
            jobs = index.jobs_matching_all(args.label)
        if not jobs:
            print("No jobs found for the given label(s).")
            sys.exit(1)
        for job in jobs:
            print(job)

    elif args.labels_cmd == "show":
        labels = index.labels_for_job(args.job)
        if not labels:
            print(f"No labels for job '{args.job}'.")
        else:
            print(", ".join(labels))
