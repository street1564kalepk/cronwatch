"""Pre/post execution hooks for cron jobs."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class HookConfig:
    """Configuration for a single hook command."""
    command: str
    timeout: int = 30
    on_failure: str = "warn"  # "warn" | "abort"


@dataclass
class JobHooks:
    """Pre and post hooks attached to a job."""
    pre: List[HookConfig] = field(default_factory=list)
    post: List[HookConfig] = field(default_factory=list)


def _run_hook(hook: HookConfig, context: dict) -> bool:
    """Execute a single hook command.

    Returns True on success, False on failure.
    Context keys are injected as environment variables.
    """
    env = {k: str(v) for k, v in context.items()}
    try:
        result = subprocess.run(
            hook.command,
            shell=True,
            timeout=hook.timeout,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            log.warning(
                "Hook command exited %d: %s\nstdout: %s\nstderr: %s",
                result.returncode,
                hook.command,
                result.stdout.strip(),
                result.stderr.strip(),
            )
            return False
        log.debug("Hook succeeded: %s", hook.command)
        return True
    except subprocess.TimeoutExpired:
        log.warning("Hook timed out after %ds: %s", hook.timeout, hook.command)
        return False
    except Exception as exc:  # pragma: no cover
        log.error("Hook raised unexpected error: %s — %s", hook.command, exc)
        return False


def run_hooks(
    hooks: List[HookConfig],
    context: dict,
    phase: str = "hook",
) -> bool:
    """Run a list of hooks in order.

    Returns True if all hooks succeeded.  A hook with on_failure='abort'
    stops execution of subsequent hooks immediately.
    """
    for hook in hooks:
        ok = _run_hook(hook, context)
        if not ok and hook.on_failure == "abort":
            log.error("Aborting remaining %s hooks due to failure.", phase)
            return False
    return True


def build_context(job_name: str, run_id: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    """Build the environment context passed to hook commands."""
    ctx: dict = {"CRONWATCH_JOB": job_name}
    if run_id is not None:
        ctx["CRONWATCH_RUN_ID"] = run_id
    if extra:
        ctx.update(extra)
    return ctx
