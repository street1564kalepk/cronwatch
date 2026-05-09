"""Flap detection: identify jobs that alternate rapidly between success and failure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatch.history import HistoryStore


@dataclass
class FlappingResult:
    job_name: str
    transitions: int  # number of success<->failure state changes
    window: int       # how many recent runs were examined
    is_flapping: bool

    def summary(self) -> str:
        status = "FLAPPING" if self.is_flapping else "stable"
        return (
            f"{self.job_name}: {status} "
            f"({self.transitions} transitions in last {self.window} runs)"
        )


def _count_transitions(outcomes: List[bool]) -> int:
    """Count how many times the outcome flips between True and False."""
    if len(outcomes) < 2:
        return 0
    return sum(
        1 for a, b in zip(outcomes, outcomes[1:]) if a != b
    )


def detect_flapping(
    store: HistoryStore,
    job_name: str,
    window: int = 10,
    threshold: int = 4,
) -> Optional[FlappingResult]:
    """Return a FlappingResult if the job is flapping, else None.

    Args:
        store: history store to read runs from.
        job_name: the job to inspect.
        window: number of most-recent finished runs to consider.
        threshold: minimum transitions to be considered flapping.
    """
    runs = [
        r for r in store.load(job_name)
        if r.exit_code is not None  # finished runs only
    ]
    recent = runs[-window:] if len(runs) >= window else runs
    if len(recent) < 2:
        return None

    outcomes = [r.exit_code == 0 for r in recent]
    transitions = _count_transitions(outcomes)
    is_flapping = transitions >= threshold

    return FlappingResult(
        job_name=job_name,
        transitions=transitions,
        window=len(recent),
        is_flapping=is_flapping,
    )


def detect_all_flapping(
    store: HistoryStore,
    job_names: List[str],
    window: int = 10,
    threshold: int = 4,
) -> List[FlappingResult]:
    """Run flap detection across all given job names; return only flapping jobs."""
    results = []
    for name in job_names:
        result = detect_flapping(store, name, window=window, threshold=threshold)
        if result and result.is_flapping:
            results.append(result)
    return results
