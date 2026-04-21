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

    registry.register(ToolSpec(name="task_plan", kind="task", params_schema={"type": "object", "properties": {"goal": {"type": "string", "description": "Human goal to decompose into steps."}}, "required": ["goal"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_plan, description="把目标拆解为简单计划，输出可执行步骤列表，供后续编排和验证使用。", param_description="goal: 需要执行的自然语言目标。", result_description="返回目标与步骤数组；每个步骤包含 id、title、action、status。", input_examples=[{"goal": "打开记事本并输入内容"}], output_examples=[{"ok": True, "tool": "task_plan", "message": "ok", "data": {"goal": "打开记事本并输入内容", "steps": []}}], safety_notes="仅做计划生成，不执行桌面动作。", implementation_notes="当前实现为轻量规划器，后续可接入更复杂的任务分解与 checkpoint."))
    registry.register(ToolSpec(name="task_state", kind="task", params_schema={"type": "object", "properties": {"task_id": {"type": "string", "description": "Task identifier."}}, "required": ["task_id"]}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=task_state, description="读取任务状态占位对象，返回步骤索引、重试次数和观测记录。", param_description="task_id: 任务标识。", result_description="返回任务 ID、步骤索引、重试次数与观测记录。", input_examples=[{"task_id": "demo"}], output_examples=[{"ok": True, "tool": "task_state", "message": "ok", "data": {"task_id": "demo", "step_index": 0, "retries": 0, "observations": []}}], safety_notes="只读任务状态，不产生任何桌面副作用。", implementation_notes="当前状态对象为进程内占位实现，后续可接入持久化 checkpoint."))
