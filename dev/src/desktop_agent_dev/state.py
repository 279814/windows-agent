from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    goal: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    step_index: int = 0
    retries: int = 0
    observations: list[str] = field(default_factory=list)
    status: str = "planned"
    last_action: dict[str, Any] | None = None
    last_error: str | None = None
    last_verified_step: int | None = None


class TaskStore:
    def __init__(self, recovery_service: Any | None = None) -> None:
        self._records: dict[str, TaskRecord] = {}
        self._recovery_service = recovery_service

    @staticmethod
    def _derive_status(record: TaskRecord) -> str:
        if record.last_error:
            return "failed"
        if record.last_verified_step is not None:
            if record.last_verified_step >= max(record.step_index, 0):
                return "verified"
        if record.last_action is not None:
            return "executing"
        return record.status or "planned"

    def upsert_plan(self, task_id: str, goal: str, steps: list[dict[str, Any]]) -> TaskRecord:
        record = self._records.get(task_id)
        if record is None:
            record = TaskRecord(task_id=task_id, goal=goal, steps=steps)
            self._records[task_id] = record
            self._persist(record)
            return record

        record.goal = goal
        record.steps = steps
        record.status = "planned"
        record.last_error = None
        self._persist(record)
        return record

    def advance(self, task_id: str, *, action: dict[str, Any] | None = None, verified: bool = False, error_message: str | None = None) -> TaskRecord:
        record = self.get(task_id)
        if action is not None:
            record.last_action = action
        if verified:
            record.last_verified_step = record.step_index
            record.last_error = None
        if error_message is not None:
            record.last_error = error_message
            record.retries += 1
        if not verified and error_message is None and record.status == "planned":
            record.status = "executing"
        record.status = self._derive_status(record)
        self._persist(record)
        return record

    def get(self, task_id: str) -> TaskRecord:
        record = self._records.get(task_id)
        if record is None:
            persisted = self._load_persisted(task_id)
            if persisted is not None:
                record = persisted
            else:
                record = TaskRecord(task_id=task_id, goal="", status="untracked")
            self._records[task_id] = record
        return record

    def _persist(self, record: TaskRecord) -> None:
        recovery_service = self._recovery_service
        if recovery_service is None:
            return
        try:
            recovery_service.sync_task(record)
        except Exception:
            return

    def _load_persisted(self, task_id: str) -> TaskRecord | None:
        recovery_service = self._recovery_service
        if recovery_service is None:
            return None
        try:
            persisted = recovery_service.load_task(task_id)
        except Exception:
            return None
        if persisted is None:
            return None
        return TaskRecord(
            task_id=persisted.task_id,
            goal=persisted.goal,
            steps=[dict(step) for step in persisted.steps],
            step_index=persisted.step_index,
            retries=persisted.retries,
            observations=list(persisted.observations),
            status=persisted.status,
            last_action=None if persisted.last_action is None else dict(persisted.last_action),
            last_error=persisted.last_error,
            last_verified_step=persisted.last_verified_step,
        )
