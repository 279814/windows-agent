from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskState:
    task_id: str
    step_index: int = 0
    retries: int = 0
    observations: list[str] = field(default_factory=list)
