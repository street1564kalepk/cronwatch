"""Tests for cronwatch.report module."""

from datetime import datetime

import pytest

from cronwatch.history import HistoryStore
from cronwatch.report import job_summary, all_jobs_summary, format_report
from cronwatch.tracker import JobRun


def _make_run(name, start, end, code):
    run = JobRun(job_name=name, started_at=start)
    run.finished_at = end
    run.exit_code = code
    return run


@pytest.fixture
def store(tmp_path):
    s = HistoryStore(str(tmp_path / "h.json"))
    runs = [
        _make_run("backup", datetime(2024, 1, 1, 2, 0), datetime(2024, 1, 1, 2, 5), 0),
        _make_run("backup", datetime(2024, 1, 2, 2, 0), datetime(2024, 1, 2, 2, 7), 1),
        _make_run("cleanup", datetime(2024, 1, 1, 3, 0), datetime(2024, 1, 1, 3, 1), 0),
    ]
    s.save(runs)
    return s


def test_job_summary_total_runs(store):
    summary = job_summary(store, "backup")
    assert summary["total_runs"] == 2


def test_job_summary_success_rate(store):
    summary = job_summary(store, "backup")
    assert summary["success_rate"] == 50.0


def test_job_summary_avg_duration(store):
    summary = job_summary(store, "backup")
    # 5*60 + 7*60 / 2 = 360
    assert summary["avg_duration_seconds"] == pytest.approx(360.0)


def test_job_summary_since_filter(store):
    summary = job_summary(store, "backup", since=datetime(2024, 1, 2))
    assert summary["total_runs"] == 1


def test_job_summary_last_run(store):
    summary = job_summary(store, "backup")
    assert summary["last_run"] is not None
    assert summary["last_run"].started_at == datetime(2024, 1, 2, 2, 0)


def test_all_jobs_summary_returns_all(store):
    summaries = all_jobs_summary(store)
    names = [s["job_name"] for s in summaries]
    assert "backup" in names
    assert "cleanup" in names


def test_format_report_contains_job_names(store):
    summaries = all_jobs_summary(store)
    report = format_report(summaries)
    assert "backup" in report
    assert "cleanup" in report


def test_format_report_empty():
    assert format_report([]) == "No job history found."


def test_job_summary_no_history(tmp_path):
    empty_store = HistoryStore(str(tmp_path / "empty.json"))
    summary = job_summary(empty_store, "ghost")
    assert summary["total_runs"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["avg_duration_seconds"] is None
