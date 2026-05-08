"""Checkpoint tracking: record mid-job progress markers for long-running cron jobs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    job_name: str
    run_id: str
    label: str
    recorded_at: datetime
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "run_id": self.run_id,
            "label": self.label,
            "recorded_at": self.recorded_at.isoformat(),
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(d: dict) -> "Checkpoint":
        return Checkpoint(
            job_name=d["job_name"],
            run_id=d["run_id"],
            label=d["label"],
            recorded_at=datetime.fromisoformat(d["recorded_at"]),
            metadata=d.get("metadata", {}),
        )


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: Dict[str, List[dict]] = {}
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._data = {}
            return
        try:
            self._data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to load checkpoints from %s: %s", self._path, exc)
            self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def record(self, checkpoint: Checkpoint) -> None:
        key = checkpoint.run_id
        self._data.setdefault(key, [])
        self._data[key].append(checkpoint.to_dict())
        self._save()
        log.debug("Checkpoint '%s' recorded for run %s", checkpoint.label, checkpoint.run_id)

    def get(self, run_id: str) -> List[Checkpoint]:
        return [Checkpoint.from_dict(d) for d in self._data.get(run_id, [])]

    def clear(self, run_id: str) -> None:
        self._data.pop(run_id, None)
        self._save()

    def last(self, run_id: str) -> Optional[Checkpoint]:
        entries = self.get(run_id)
        return entries[-1] if entries else None


def make_checkpoint(
    job_name: str,
    run_id: str,
    label: str,
    metadata: Optional[Dict[str, str]] = None,
) -> Checkpoint:
    return Checkpoint(
        job_name=job_name,
        run_id=run_id,
        label=label,
        recorded_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
