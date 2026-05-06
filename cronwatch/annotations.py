"""Job run annotation support — attach notes or labels to historical runs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Annotation:
    run_id: str
    job_name: str
    note: str
    author: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "job_name": self.job_name,
            "note": self.note,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "Annotation":
        return Annotation(
            run_id=d["run_id"],
            job_name=d["job_name"],
            note=d["note"],
            author=d["author"],
            created_at=datetime.fromisoformat(d["created_at"]),
        )


class AnnotationStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: Dict[str, List[Annotation]] = {}
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self._path.read_text())
            self._data = {
                run_id: [Annotation.from_dict(a) for a in entries]
                for run_id, entries in raw.items()
            }
        except Exception:
            log.warning("Failed to load annotations from %s", self._path)
            self._data = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            run_id: [a.to_dict() for a in entries]
            for run_id, entries in self._data.items()
        }
        self._path.write_text(json.dumps(raw, indent=2))

    def add(self, annotation: Annotation) -> None:
        self._data.setdefault(annotation.run_id, []).append(annotation)
        self.save()
        log.debug("Annotated run %s: %s", annotation.run_id, annotation.note)

    def get(self, run_id: str) -> List[Annotation]:
        return list(self._data.get(run_id, []))

    def for_job(self, job_name: str) -> List[Annotation]:
        result: List[Annotation] = []
        for entries in self._data.values():
            result.extend(a for a in entries if a.job_name == job_name)
        return sorted(result, key=lambda a: a.created_at)

    def delete(self, run_id: str) -> int:
        removed = len(self._data.pop(run_id, []))
        if removed:
            self.save()
        return removed

    def all_run_ids(self) -> List[str]:
        return list(self._data.keys())
