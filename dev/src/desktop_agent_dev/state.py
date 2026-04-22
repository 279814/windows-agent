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


class TaskStore:
    def __init__(self) -> None:
        self._records: dict[str, TaskRecord] = {}

    def upsert_plan(self, task_id: str, goal: str, steps: list[dict[str, Any]]) -> TaskRecord:
        record = self._records.get(task_id)
        if record is None:
            record = TaskRecord(task_id=task_id, goal=goal, steps=steps)
            self._records[task_id] = record
            return record

        record.goal = goal
        record.steps = steps
        record.status = "planned"
        return record

    def get(self, task_id: str) -> TaskRecord:
        record = self._records.get(task_id)
        if record is None:
            record = TaskRecord(task_id=task_id, goal="", status="untracked")
            self._records[task_id] = record
        return record
