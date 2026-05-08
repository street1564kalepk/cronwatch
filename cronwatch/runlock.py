"""Run-lock tracking: detect and prevent concurrent execution of the same job."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict


@dataclass
class LockEntry:
    job_name: str
    pid: int
    started_at: float  # Unix timestamp

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "LockEntry":
        return LockEntry(
            job_name=d["job_name"],
            pid=d["pid"],
            started_at=d["started_at"],
        )


def _pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* is currently running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


class RunLockStore:
    """Persist active run-locks to a JSON file and query them."""

    def __init__(self, path: str = ".cronwatch_runlocks.json") -> None:
        self._path = Path(path)

    def _load_raw(self) -> Dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_raw(self, data: Dict[str, dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2))

    def acquire(self, job_name: str, pid: Optional[int] = None) -> LockEntry:
        """Record that *job_name* is now running under *pid*."""
        entry = LockEntry(
            job_name=job_name,
            pid=pid if pid is not None else os.getpid(),
            started_at=time.time(),
        )
        data = self._load_raw()
        data[job_name] = entry.to_dict()
        self._save_raw(data)
        return entry

    def release(self, job_name: str) -> bool:
        """Remove the lock for *job_name*. Returns True if a lock existed."""
        data = self._load_raw()
        if job_name not in data:
            return False
        del data[job_name]
        self._save_raw(data)
        return True

    def is_locked(self, job_name: str) -> bool:
        """Return True if *job_name* has an active (live-process) lock."""
        data = self._load_raw()
        if job_name not in data:
            return False
        entry = LockEntry.from_dict(data[job_name])
        if _pid_alive(entry.pid):
            return True
        # Stale lock — clean it up automatically
        self.release(job_name)
        return False

    def all_locks(self) -> list[LockEntry]:
        """Return all currently-stored lock entries (including potentially stale ones)."""
        return [LockEntry.from_dict(v) for v in self._load_raw().values()]
