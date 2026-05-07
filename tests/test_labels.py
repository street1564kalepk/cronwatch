"""Tests for cronwatch.labels."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.labels import LabelIndex, build_label_index


@pytest.fixture()
def index() -> LabelIndex:
    idx = LabelIndex()
    idx.add("backup", ["critical", "storage"])
    idx.add("report", ["critical", "reporting"])
    idx.add("cleanup", ["storage"])
    return idx


def test_jobs_for_label_returns_correct_jobs(index: LabelIndex) -> None:
    assert index.jobs_for_label("critical") == ["backup", "report"]


def test_jobs_for_label_unknown_returns_empty(index: LabelIndex) -> None:
    assert index.jobs_for_label("nonexistent") == []


def test_labels_for_job_returns_sorted(index: LabelIndex) -> None:
    assert index.labels_for_job("backup") == ["critical", "storage"]


def test_labels_for_job_unknown_returns_empty(index: LabelIndex) -> None:
    assert index.labels_for_job("ghost") == []


def test_all_labels_sorted(index: LabelIndex) -> None:
    assert index.all_labels() == ["critical", "reporting", "storage"]


def test_jobs_matching_all_single_label(index: LabelIndex) -> None:
    assert index.jobs_matching_all(["storage"]) == ["backup", "cleanup"]


def test_jobs_matching_all_multiple_labels(index: LabelIndex) -> None:
    assert index.jobs_matching_all(["critical", "storage"]) == ["backup"]


def test_jobs_matching_all_empty_returns_empty(index: LabelIndex) -> None:
    assert index.jobs_matching_all([]) == []


def test_jobs_matching_all_no_intersection(index: LabelIndex) -> None:
    assert index.jobs_matching_all(["reporting", "storage"]) == []


def test_build_label_index_from_config() -> None:
    job_a = MagicMock(name="job_a", spec=["name", "labels"])
    job_a.name = "job_a"
    job_a.labels = ["env:prod", "team:ops"]

    job_b = MagicMock(name="job_b", spec=["name", "labels"])
    job_b.name = "job_b"
    job_b.labels = None

    config = MagicMock()
    config.jobs = [job_a, job_b]

    idx = build_label_index(config)
    assert idx.jobs_for_label("env:prod") == ["job_a"]
    assert idx.labels_for_job("job_b") == []
