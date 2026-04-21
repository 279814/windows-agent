from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..schemas import ok
from ..state import TaskState
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_task_tools(registry: ToolRegistry, services: Any) -> None:
    def task_plan(goal: str) -> dict[str, Any]:
        plan = services.planner.create_plan(goal)
        return ok("task_plan", {"goal": plan.goal, "steps": [asdict(step) for step in plan.steps]})

    def task_state(task_id: str) -> dict[str, Any]:
        state = TaskState(task_id=task_id)
        return ok(
            "task_state",
            {
                "task_id": state.task_id,
                "step_index": state.step_index,
                "retries": state.retries,
                "observations": state.observations,
            },
        )

    registry.register(
        ToolSpec(
            name="task_plan",
            kind="task",
            params_schema={"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
            result_schema=RESULT_SCHEMAS["default"],
            permission=None,
            executor=task_plan,
            description="把目标拆解为简单计划。",
            examples=[{"goal": "打开记事本并输入内容"}],
        )
    )
    registry.register(
        ToolSpec(
            name="task_state",
            kind="task",
            params_schema={"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
            result_schema=RESULT_SCHEMAS["default"],
            permission=None,
            executor=task_state,
            description="读取任务状态占位对象。",
            examples=[{"task_id": "demo"}],
        )
    )
