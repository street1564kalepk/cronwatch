"""Tests for cronwatch.tags."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.tags import (
    TagIndex,
    build_tag_index,
    filter_runs_by_tag,
    group_runs_by_tag,
)
from cronwatch.tracker import JobRun


def _run(job_name: str) -> JobRun:
    run = MagicMock(spec=JobRun)
    run.job_name = job_name
    return run


def _cfg(name: str, tags: list[str]):
    cfg = MagicMock()
    cfg.name = name
    cfg.tags = tags
    return cfg


@pytest.fixture()
def index() -> TagIndex:
    idx = TagIndex()
    idx.add("backup", ["daily", "storage"])
    idx.add("cleanup", ["daily"])
    idx.add("report", ["weekly"])
    return idx


def test_jobs_for_tag_returns_correct_jobs(index):
    assert set(index.jobs_for_tag("daily")) == {"backup", "cleanup"}


def test_jobs_for_tag_unknown_returns_empty(index):
    assert index.jobs_for_tag("nonexistent") == []


def test_tags_for_job(index):
    assert set(index.tags_for_job("backup")) == {"daily", "storage"}


def test_all_tags_sorted(index):
    assert index.all_tags() == ["daily", "storage", "weekly"]


def test_build_tag_index_from_configs():
    cfgs = [_cfg("a", ["x", "y"]), _cfg("b", ["y"]), _cfg("c", [])]
    idx = build_tag_index(cfgs)
    assert set(idx.jobs_for_tag("x")) == {"a"}
    assert set(idx.jobs_for_tag("y")) == {"a", "b"}
    assert idx.jobs_for_tag("z") == []


def test_filter_runs_by_tag(index):
    runs = [_run("backup"), _run("report"), _run("cleanup")]
    result = filter_runs_by_tag(runs, "daily", index)
    names = {r.job_name for r in result}
    assert names == {"backup", "cleanup"}


def test_filter_runs_by_tag_unknown(index):
    runs = [_run("backup")]
    assert filter_runs_by_tag(runs, "nonexistent", index) == []


def test_group_runs_by_tag(index):
    runs = [_run("backup"), _run("cleanup"), _run("report")]
    groups = group_runs_by_tag(runs, index)
    assert set(groups["daily"]) == {runs[0], runs[1]}
    assert groups["weekly"] == [runs[2]]
    assert "storage" in groups
