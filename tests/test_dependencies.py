"""Tests for cronwatch.dependencies."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.dependencies import (
    DependencyGraph,
    load_dependency_graph,
    save_dependency_graph,
)


@pytest.fixture()
def graph() -> DependencyGraph:
    g = DependencyGraph()
    g.add("job_b", ["job_a"])
    g.add("job_c", ["job_a", "job_b"])
    return g


def test_dependencies_of_returns_correct_deps(graph: DependencyGraph) -> None:
    assert graph.dependencies_of("job_c") == ["job_a", "job_b"]


def test_dependencies_of_unknown_job_returns_empty(graph: DependencyGraph) -> None:
    assert graph.dependencies_of("nonexistent") == []


def test_dependents_of_returns_correct_jobs(graph: DependencyGraph) -> None:
    assert graph.dependents_of("job_a") == ["job_b", "job_c"]


def test_dependents_of_leaf_returns_empty(graph: DependencyGraph) -> None:
    assert graph.dependents_of("job_c") == []


def test_is_satisfied_all_deps_met(graph: DependencyGraph) -> None:
    assert graph.is_satisfied("job_c", {"job_a", "job_b"}) is True


def test_is_satisfied_missing_dep(graph: DependencyGraph) -> None:
    assert graph.is_satisfied("job_c", {"job_a"}) is False


def test_is_satisfied_no_deps(graph: DependencyGraph) -> None:
    assert graph.is_satisfied("job_a", set()) is True


def test_unsatisfied_returns_missing(graph: DependencyGraph) -> None:
    assert graph.unsatisfied("job_c", {"job_a"}) == ["job_b"]


def test_all_jobs_includes_implicit_jobs(graph: DependencyGraph) -> None:
    jobs = graph.all_jobs()
    assert "job_a" in jobs
    assert "job_b" in jobs
    assert "job_c" in jobs


def test_save_and_load_roundtrip(tmp_path: Path, graph: DependencyGraph) -> None:
    dest = tmp_path / "deps.json"
    save_dependency_graph(graph, dest)
    loaded = load_dependency_graph(dest)
    assert loaded.dependencies_of("job_b") == ["job_a"]
    assert loaded.dependencies_of("job_c") == ["job_a", "job_b"]


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    g = load_dependency_graph(tmp_path / "missing.json")
    assert g.all_jobs() == []


def test_save_creates_valid_json(tmp_path: Path, graph: DependencyGraph) -> None:
    dest = tmp_path / "deps.json"
    save_dependency_graph(graph, dest)
    data = json.loads(dest.read_text())
    assert "job_b" in data
    assert "job_a" in data["job_b"]
