from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskStep:
    name: str
    description: str
    expected_result: str = ""


@dataclass(slots=True)
class TaskPlan:
    goal: str
    steps: list[TaskStep] = field(default_factory=list)


class Planner:
    def create_plan(self, goal: str) -> TaskPlan:
        return TaskPlan(
            goal=goal,
            steps=[
                TaskStep(
                    name="observe",
                    description="Read the current desktop/app state before acting.",
                    expected_result="Observation captured",
                ),
                TaskStep(
                    name="execute",
                    description="Perform the requested task using the safest available action.",
                    expected_result="Task action completed",
                ),
                TaskStep(
                    name="verify",
                    description="Confirm the action produced the expected result.",
                    expected_result="Verification passed",
                ),
            ],
        )
