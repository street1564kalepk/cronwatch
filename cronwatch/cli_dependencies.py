"""CLI sub-command for managing job dependencies."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.dependencies import (
    DependencyGraph,
    load_dependency_graph,
    save_dependency_graph,
)

_DEFAULT_PATH = Path("cronwatch_deps.json")


def build_dependencies_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("deps", help="Manage job dependencies")
    sub = p.add_subparsers(dest="deps_cmd", required=True)

    add_p = sub.add_parser("add", help="Add dependency edges")
    add_p.add_argument("job", help="Job that depends on others")
    add_p.add_argument("depends_on", nargs="+", metavar="DEP",
                       help="Jobs that must succeed first")
    add_p.add_argument("--file", default=str(_DEFAULT_PATH), metavar="PATH")

    show_p = sub.add_parser("show", help="Show dependencies for a job")
    show_p.add_argument("job", help="Job name to inspect")
    show_p.add_argument("--file", default=str(_DEFAULT_PATH), metavar="PATH")

    list_p = sub.add_parser("list", help="List all dependency edges")
    list_p.add_argument("--file", default=str(_DEFAULT_PATH), metavar="PATH")

    p.set_defaults(func=run_dependencies)


def run_dependencies(args: argparse.Namespace) -> None:
    path = Path(args.file)
    graph = load_dependency_graph(path)

    if args.deps_cmd == "add":
        graph.add(args.job, args.depends_on)
        save_dependency_graph(graph, path)
        print(f"Added: {args.job} depends on {args.depends_on}")

    elif args.deps_cmd == "show":
        deps = graph.dependencies_of(args.job)
        dependents = graph.dependents_of(args.job)
        if not deps and not dependents:
            print(f"No dependency information for job '{args.job}'.")
            sys.exit(0)
        if deps:
            print(f"{args.job} depends on:")
            for d in deps:
                print(f"  - {d}")
        if dependents:
            print(f"Jobs that depend on {args.job}:")
            for d in dependents:
                print(f"  - {d}")

    elif args.deps_cmd == "list":
        jobs = graph.all_jobs()
        if not jobs:
            print("No dependencies defined.")
            sys.exit(0)
        for job in jobs:
            deps = graph.dependencies_of(job)
            if deps:
                print(f"{job}: {', '.join(deps)}")
