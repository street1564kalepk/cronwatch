"""Label-based filtering and grouping for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from cronwatch.config import CronwatchConfig


@dataclass
class LabelIndex:
    """Bidirectional index mapping labels to jobs and jobs to labels."""

    _label_to_jobs: Dict[str, Set[str]] = field(default_factory=dict)
    _job_to_labels: Dict[str, Set[str]] = field(default_factory=dict)

    def add(self, job_name: str, labels: List[str]) -> None:
        """Register *labels* for *job_name*."""
        for label in labels:
            self._label_to_jobs.setdefault(label, set()).add(job_name)
        self._job_to_labels.setdefault(job_name, set()).update(labels)

    def jobs_for_label(self, label: str) -> List[str]:
        """Return sorted list of job names that carry *label*."""
        return sorted(self._label_to_jobs.get(label, set()))

    def labels_for_job(self, job_name: str) -> List[str]:
        """Return sorted list of labels attached to *job_name*."""
        return sorted(self._job_to_labels.get(job_name, set()))

    def all_labels(self) -> List[str]:
        """Return sorted list of every known label."""
        return sorted(self._label_to_jobs.keys())

    def jobs_matching_all(self, labels: List[str]) -> List[str]:
        """Return jobs that carry ALL of the supplied *labels*."""
        if not labels:
            return []
        sets = [self._label_to_jobs.get(lbl, set()) for lbl in labels]
        return sorted(sets[0].intersection(*sets[1:]))


def build_label_index(config: CronwatchConfig) -> LabelIndex:
    """Construct a :class:`LabelIndex` from a loaded config."""
    index = LabelIndex()
    for job in config.jobs:
        labels = getattr(job, "labels", None) or []
        if labels:
            index.add(job.name, labels)
    return index
