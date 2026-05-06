"""Job dependency tracking — ensures jobs run in the correct order."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

log = logging.getLogger(__name__)


class DependencyGraph:
    """Tracks which jobs depend on which other jobs."""

    def __init__(self) -> None:
        # job_name -> set of job names it depends on
        self._deps: Dict[str, Set[str]] = {}

    def add(self, job: str, depends_on: List[str]) -> None:
        """Register dependencies for a job."""
        self._deps.setdefault(job, set()).update(depends_on)
        log.debug("Job %r depends on %r", job, depends_on)

    def dependencies_of(self, job: str) -> List[str]:
        """Return the list of jobs that *job* depends on."""
        return sorted(self._deps.get(job, set()))

    def dependents_of(self, job: str) -> List[str]:
        """Return jobs that depend on *job*."""
        return sorted(j for j, deps in self._deps.items() if job in deps)

    def is_satisfied(self, job: str, succeeded_jobs: Set[str]) -> bool:
        """Return True if all dependencies of *job* have succeeded."""
        return self._deps.get(job, set()).issubset(succeeded_jobs)

    def unsatisfied(self, job: str, succeeded_jobs: Set[str]) -> List[str]:
        """Return dependency names that have not yet succeeded."""
        return sorted(self._deps.get(job, set()) - succeeded_jobs)

    def all_jobs(self) -> List[str]:
        """Return every job name known to the graph."""
        names: Set[str] = set(self._deps.keys())
        for deps in self._deps.values():
            names.update(deps)
        return sorted(names)


def load_dependency_graph(path: Path) -> DependencyGraph:
    """Load a DependencyGraph from a JSON file.

    Expected format::

        {"job_a": ["job_b", "job_c"], ...}
    """
    graph = DependencyGraph()
    if not path.exists():
        log.debug("Dependency file %s not found, returning empty graph", path)
        return graph
    with path.open() as fh:
        data: Dict[str, List[str]] = json.load(fh)
    for job, deps in data.items():
        graph.add(job, deps)
    return graph


def save_dependency_graph(graph: DependencyGraph, path: Path) -> None:
    """Persist *graph* to *path* as JSON."""
    data = {job: graph.dependencies_of(job) for job in graph.all_jobs()
            if graph.dependencies_of(job)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(data, fh, indent=2)
    log.debug("Saved dependency graph to %s", path)
