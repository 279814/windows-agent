from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskStep:
    step_index: int
    name: str
    description: str
    expected_result: str = ""


@dataclass(slots=True)
class TaskPlan:
    task_id: str
    goal: str
    steps: list[TaskStep] = field(default_factory=list)


class Planner:
    def create_plan(self, goal: str) -> TaskPlan:
        task_id = f"plan-{abs(hash(goal)) & 0xFFFF_FFFF:x}"
        return TaskPlan(
            task_id=task_id,
            goal=goal,
            steps=[
                TaskStep(
                    step_index=0,
                    name="observe",
                    description="Read the current desktop/app state before acting.",
                    expected_result="Observation captured",
                ),
                TaskStep(
                    step_index=1,
                    name="execute",
                    description="Perform the requested task using the safest available action.",
                    expected_result="Task action completed",
                ),
                TaskStep(
                    step_index=2,
                    name="verify",
                    description="Confirm the action produced the expected result.",
                    expected_result="Verification passed",
                ),
            ],
        )
