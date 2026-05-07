"""Tests for cronwatch.hooks."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.hooks import (
    HookConfig,
    JobHooks,
    _run_hook,
    build_context,
    run_hooks,
)


# ---------------------------------------------------------------------------
# _run_hook
# ---------------------------------------------------------------------------

def test_run_hook_success():
    hook = HookConfig(command="true", timeout=5)
    assert _run_hook(hook, {}) is True


def test_run_hook_failure_nonzero():
    hook = HookConfig(command="false", timeout=5)
    assert _run_hook(hook, {}) is False


def test_run_hook_timeout():
    hook = HookConfig(command="sleep 60", timeout=1)
    # subprocess.run raises TimeoutExpired which _run_hook catches
    result = _run_hook(hook, {})
    assert result is False


def test_run_hook_injects_context(tmp_path):
    output = tmp_path / "out.txt"
    hook = HookConfig(command=f"echo $CRONWATCH_JOB > {output}", timeout=5)
    ctx = build_context("backup")
    _run_hook(hook, ctx)
    assert output.read_text().strip() == "backup"


# ---------------------------------------------------------------------------
# run_hooks
# ---------------------------------------------------------------------------

def test_run_hooks_all_succeed():
    hooks = [HookConfig(command="true"), HookConfig(command="true")]
    assert run_hooks(hooks, {}) is True


def test_run_hooks_warn_continues_on_failure():
    """on_failure='warn' should not abort remaining hooks."""
    results = []

    def fake_run(hook, ctx):
        results.append(hook.command)
        return hook.command != "false"

    hooks = [
        HookConfig(command="false", on_failure="warn"),
        HookConfig(command="true", on_failure="warn"),
    ]
    with patch("cronwatch.hooks._run_hook", side_effect=fake_run):
        ok = run_hooks(hooks, {})

    assert "true" in results, "second hook should still run"
    assert ok is True  # all hooks ran; overall return is True


def test_run_hooks_abort_stops_on_failure():
    """on_failure='abort' should stop subsequent hooks."""
    results = []

    def fake_run(hook, ctx):
        results.append(hook.command)
        return hook.command != "false"

    hooks = [
        HookConfig(command="false", on_failure="abort"),
        HookConfig(command="true"),
    ]
    with patch("cronwatch.hooks._run_hook", side_effect=fake_run):
        ok = run_hooks(hooks, {})

    assert "true" not in results, "second hook must not run after abort"
    assert ok is False


def test_run_hooks_empty_list():
    assert run_hooks([], {}) is True


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------

def test_build_context_basic():
    ctx = build_context("my_job")
    assert ctx["CRONWATCH_JOB"] == "my_job"


def test_build_context_with_run_id():
    ctx = build_context("my_job", run_id="abc123")
    assert ctx["CRONWATCH_RUN_ID"] == "abc123"


def test_build_context_extra_keys():
    ctx = build_context("my_job", extra={"CUSTOM": "value"})
    assert ctx["CUSTOM"] == "value"
    assert ctx["CRONWATCH_JOB"] == "my_job"


# ---------------------------------------------------------------------------
# JobHooks dataclass
# ---------------------------------------------------------------------------

def test_job_hooks_defaults():
    jh = JobHooks()
    assert jh.pre == []
    assert jh.post == []
