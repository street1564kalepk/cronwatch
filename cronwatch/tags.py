"""Tag-based filtering and grouping for cron jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from cronwatch.tracker import JobRun


@dataclass
class TagIndex:
    """Maps tag names to lists of job names."""

    _index: Dict[str, List[str]] = field(default_factory=dict)

    def add(self, job_name: str, tags: Iterable[str]) -> None:
        """Register a job under each of its tags."""
        for tag in tags:
            self._index.setdefault(tag, []).append(job_name)

    def jobs_for_tag(self, tag: str) -> List[str]:
        """Return job names associated with *tag*."""
        return list(self._index.get(tag, []))

    def tags_for_job(self, job_name: str) -> List[str]:
        """Return all tags that include *job_name*."""
        return [tag for tag, jobs in self._index.items() if job_name in jobs]

    def all_tags(self) -> List[str]:
        return sorted(self._index.keys())


def build_tag_index(job_configs: Iterable) -> TagIndex:
    """Build a TagIndex from an iterable of JobConfig objects."""
    index = TagIndex()
    for cfg in job_configs:
        tags = getattr(cfg, "tags", None) or []
        index.add(cfg.name, tags)
    return index


def filter_runs_by_tag(
    runs: Iterable[JobRun],
    tag: str,
    index: TagIndex,
) -> List[JobRun]:
    """Return only runs whose job name belongs to *tag*."""
    tagged_jobs = set(index.jobs_for_tag(tag))
    return [r for r in runs if r.job_name in tagged_jobs]


def group_runs_by_tag(
    runs: Iterable[JobRun],
    index: TagIndex,
) -> Dict[str, List[JobRun]]:
    """Group runs by tag; a run may appear under multiple tags."""
    groups: Dict[str, List[JobRun]] = {}
    run_list = list(runs)
    for tag in index.all_tags():
        tagged = filter_runs_by_tag(run_list, tag, index)
        if tagged:
            groups[tag] = tagged
    return groups
