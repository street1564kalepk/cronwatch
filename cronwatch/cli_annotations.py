"""CLI sub-commands for managing job run annotations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.annotations import Annotation, AnnotationStore


def build_annotations_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("annotate", help="Manage run annotations")
    sub = p.add_subparsers(dest="ann_cmd", required=True)

    add_p = sub.add_parser("add", help="Add an annotation to a run")
    add_p.add_argument("run_id", help="Run ID to annotate")
    add_p.add_argument("job_name", help="Job name the run belongs to")
    add_p.add_argument("note", help="Annotation text")
    add_p.add_argument("--author", default="cli", help="Author name (default: cli)")

    show_p = sub.add_parser("show", help="Show annotations for a run")
    show_p.add_argument("run_id", help="Run ID")

    job_p = sub.add_parser("job", help="Show all annotations for a job")
    job_p.add_argument("job_name", help="Job name")

    del_p = sub.add_parser("delete", help="Delete all annotations for a run")
    del_p.add_argument("run_id", help="Run ID")

    for sp in (add_p, show_p, job_p, del_p):
        sp.add_argument(
            "--store",
            default=".cronwatch/annotations.json",
            metavar="PATH",
            help="Path to annotation store (default: .cronwatch/annotations.json)",
        )


def run_annotations(args: argparse.Namespace) -> None:
    store = AnnotationStore(Path(args.store))

    if args.ann_cmd == "add":
        ann = Annotation(
            run_id=args.run_id,
            job_name=args.job_name,
            note=args.note,
            author=args.author,
        )
        store.add(ann)
        print(f"Annotation added to run {args.run_id!r}.")

    elif args.ann_cmd == "show":
        entries = store.get(args.run_id)
        if not entries:
            print(f"No annotations for run {args.run_id!r}.")
            return
        for a in entries:
            print(f"[{a.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {a.author}: {a.note}")

    elif args.ann_cmd == "job":
        entries = store.for_job(args.job_name)
        if not entries:
            print(f"No annotations for job {args.job_name!r}.")
            return
        for a in entries:
            print(
                f"  run={a.run_id}  [{a.created_at.strftime('%Y-%m-%d %H:%M:%S')}]"
                f"  {a.author}: {a.note}"
            )

    elif args.ann_cmd == "delete":
        removed = store.delete(args.run_id)
        if removed:
            print(f"Deleted {removed} annotation(s) for run {args.run_id!r}.")
        else:
            print(f"No annotations found for run {args.run_id!r}.")
            sys.exit(1)
