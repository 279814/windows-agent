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
    def __init__(self) -> None:
        self._records: dict[str, TaskRecord] = {}

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
            return record

        record.goal = goal
        record.steps = steps
        record.status = "planned"
        record.last_error = None
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
        return record

    def get(self, task_id: str) -> TaskRecord:
        record = self._records.get(task_id)
        if record is None:
            record = TaskRecord(task_id=task_id, goal="", status="untracked")
            self._records[task_id] = record
        return record
