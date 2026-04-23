from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import TaskCheckpoint, TaskRecoveryRecord


class RecoveryStore:
    """File-backed recovery store using JSON/JSONL for easy local integration."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.tasks_dir = self.root / "tasks"
        self.checkpoints_dir = self.root / "checkpoints"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def checkpoint_path(self, task_id: str) -> Path:
        return self.checkpoints_dir / f"{task_id}.jsonl"

    def save_task(self, record: TaskRecoveryRecord) -> TaskRecoveryRecord:
        self._atomic_write_json(self.task_path(record.task_id), record.to_dict())
        return record

    def load_task(self, task_id: str) -> TaskRecoveryRecord | None:
        path = self.task_path(task_id)
        if not path.exists():
            return None
        return TaskRecoveryRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def append_checkpoint(self, checkpoint: TaskCheckpoint) -> TaskCheckpoint:
        path = self.checkpoint_path(checkpoint.task_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(checkpoint.to_dict(), ensure_ascii=True))
            handle.write("\n")
        return checkpoint

    def load_checkpoints(self, task_id: str, *, limit: int | None = None) -> list[TaskCheckpoint]:
        path = self.checkpoint_path(task_id)
        if not path.exists():
            return []
        rows = [
            TaskCheckpoint.from_dict(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if limit is not None and limit >= 0:
            return rows[-limit:]
        return rows

    def load_latest_checkpoint(self, task_id: str) -> TaskCheckpoint | None:
        checkpoints = self.load_checkpoints(task_id, limit=1)
        return checkpoints[0] if checkpoints else None

    def list_tasks(self) -> Iterable[str]:
        for path in sorted(self.tasks_dir.glob("*.json")):
            yield path.stem

    def _atomic_write_json(self, path: Path, payload: dict[str, object]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        tmp_path.replace(path)
