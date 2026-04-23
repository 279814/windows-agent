from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..schemas import ok
from ..state import TaskStore
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_task_tools(registry: ToolRegistry, services: Any) -> None:
    task_store = getattr(services, "task_store", None) or TaskStore()
    services.task_store = task_store

    def task_plan(goal: str) -> dict[str, Any]:
        plan = services.planner.create_plan(goal)
        steps = [asdict(step) for step in plan.steps]
        record = task_store.upsert_plan(plan.task_id, plan.goal, steps)
        return {
            "ok": True,
            "tool": "task_plan",
            "message": "ok",
            "data": {
                "task_id": record.task_id,
                "goal": record.goal,
                "steps": record.steps,
                "step_index": record.step_index,
                "retries": record.retries,
                "observations": record.observations,
                "status": record.status,
                "last_action": record.last_action,
                "last_error": record.last_error,
                "last_verified_step": record.last_verified_step,
            },
            "error": None,
        }

    def task_state(task_id: str) -> dict[str, Any]:
        state = task_store.get(task_id)
        return {
            "ok": True,
            "tool": "task_state",
            "message": "ok",
            "data": {
                "task_id": state.task_id,
                "goal": state.goal,
                "steps": state.steps,
                "step_index": state.step_index,
                "retries": state.retries,
                "observations": state.observations,
                "status": state.status,
                "last_action": state.last_action,
                "last_error": state.last_error,
                "last_verified_step": state.last_verified_step,
            },
            "error": None,
        }

    registry.register(ToolSpec(name="task_plan", kind="task", params_schema={"type": "object", "properties": {"goal": {"type": "string", "description": "Human goal to decompose into steps."}}, "required": ["goal"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_plan, description="Break a goal into an executable plan and register a trackable task instance. Use this when you need ordered steps before any desktop action is taken.\n\nParameters: goal is the natural-language objective to decompose.\nReturns: a task id, goal, steps, current step index, retries, observations, and task status. Successful responses always include error: null.\nSafety: planning only; no desktop actions are executed.\nBehavior note: the returned plan is meant to support an end-to-end loop of observe -> act -> verify over the desktop state.\nExamples: {\"goal\": \"open notepad and enter content\"}.", param_description="goal: natural-language objective to decompose.", result_description="Returns the task id, goal, steps, current step index, retries, observations, and task status.", input_examples=[{"goal": "对当前桌面执行一次观察、点击、输入、快捷键、窗口操作的阶段验收，并在每一步前后验证状态变化"}], output_examples=[{"ok": True, "tool": "task_plan", "message": "ok", "data": {"task_id": "plan-1234abcd", "goal": "对当前桌面执行一次观察、点击、输入、快捷键、窗口操作的阶段验收，并在每一步前后验证状态变化", "steps": [{"step_index": 0, "name": "observe", "description": "Read the current desktop/app state before acting.", "expected_result": "Observation captured"}, {"step_index": 1, "name": "execute", "description": "Perform the requested task using the safest available action.", "expected_result": "Task action completed"}, {"step_index": 2, "name": "verify", "description": "Confirm the action produced the expected result.", "expected_result": "Verification passed"}], "step_index": 0, "retries": 0, "observations": [], "status": "planned"}, "error": None}], safety_notes="Planning only; no desktop actions are executed.", implementation_notes="Creates a persistent task record that task_state can retrieve."))
    registry.register(ToolSpec(name="task_state", kind="task", params_schema={"type": "object", "properties": {"task_id": {"type": "string", "description": "Task identifier."}}, "required": ["task_id"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_state, description="Read the current state of a tracked task instance. Use this to inspect progress, retries, and observations without mutating anything.\n\nParameters: task_id identifies the tracked task.\nReturns: the task id, goal, steps, step index, retry count, observations, and lifecycle status. If the task has not been planned yet, a placeholder untracked record is returned. Successful responses always include error: null.\nSafety: read-only task status; no desktop side effects.\nBehavior note: use this to verify the latest observe -> act -> verify progress after each desktop action.\nExamples: {\"task_id\": \"demo\"}.", param_description="task_id: tracked task identifier.", result_description="Returns the task id, goal, steps, step index, retry count, observations, and lifecycle status.", input_examples=[{"task_id": "phase1-final-retest"}], output_examples=[{"ok": True, "tool": "task_state", "message": "ok", "data": {"task_id": "phase1-final-retest", "goal": "对当前桌面执行一次观察、点击、输入、快捷键、窗口操作的阶段验收，并在每一步前后验证状态变化", "steps": [{"step_index": 0, "name": "observe", "description": "Read the current desktop/app state before acting.", "expected_result": "Observation captured"}, {"step_index": 1, "name": "execute", "description": "Perform the requested task using the safest available action.", "expected_result": "Task action completed"}, {"step_index": 2, "name": "verify", "description": "Confirm the action produced the expected result.", "expected_result": "Verification passed"}], "step_index": 0, "retries": 0, "observations": [], "status": "planned"}, "error": None}], safety_notes="Read-only task status; no desktop side effects.", implementation_notes="Reads the persisted task record created by task_plan."))
