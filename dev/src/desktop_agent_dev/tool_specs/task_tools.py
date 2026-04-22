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

    registry.register(ToolSpec(name="task_plan", kind="task", params_schema={"type": "object", "properties": {"goal": {"type": "string", "description": "Human goal to decompose into steps."}}, "required": ["goal"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_plan, description="Break a goal into an executable plan. Use this when you need ordered steps before any desktop action is taken.\n\nParameters: goal is the natural-language objective to decompose.\nReturns: the goal plus a steps array; each step includes id, title, action, and status.\nSafety: planning only; no desktop actions are executed.\nExamples: {\"goal\": \"open notepad and enter content\"}.", param_description="goal: natural-language objective to decompose.", result_description="Returns the goal plus a steps array with id, title, action, and status.", input_examples=[{"goal": "打开记事本并输入内容"}], output_examples=[{"ok": True, "tool": "task_plan", "message": "ok", "data": {"goal": "打开记事本并输入内容", "steps": []}}], safety_notes="Planning only; no desktop actions are executed.", implementation_notes="Uses the lightweight planner and returns the structured step list."))
    registry.register(ToolSpec(name="task_state", kind="task", params_schema={"type": "object", "properties": {"task_id": {"type": "string", "description": "Task identifier."}}, "required": ["task_id"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_state, description="Read the current state of a tracked task. Use this to inspect progress, retries, and observations without mutating anything.\n\nParameters: task_id identifies the tracked task.\nReturns: the task ID, step index, retry count, and observations list.\nSafety: read-only task status; no desktop side effects.\nExamples: {\"task_id\": \"demo\"}.", param_description="task_id: tracked task identifier.", result_description="Returns the task ID, step index, retry count, and observations list.", input_examples=[{"task_id": "demo"}], output_examples=[{"ok": True, "tool": "task_state", "message": "ok", "data": {"task_id": "demo", "step_index": 0, "retries": 0, "observations": []}}], safety_notes="Read-only task status; no desktop side effects.", implementation_notes="Creates an in-process state object and serializes its fields."))
