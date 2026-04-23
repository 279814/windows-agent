from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


MOTION_PREVIEW_OUTPUT_EXAMPLES = [
    {
        "ok": True,
        "tool": "motion_preview",
        "message": "ok",
        "data": {
            "action": "motion_preview",
            "ok": True,
            "detail": "motion planned",
            "payload": {
                "kind": "drag",
                "start": {"x": 10, "y": 10},
                "end": {"x": 100, "y": 100},
                "duration_ms": 180,
                "path": [{"x": 10, "y": 10, "t": 0.0}, {"x": 100, "y": 100, "t": 1.0}],
            },
        },
        "error": None,
    }
]


def register_motion_tools(registry: ToolRegistry, services: Any) -> None:
    motion_schema = {
        "type": "object",
        "properties": {
            "kind": {"type": "string"},
            "start_x": {"type": "integer"},
            "start_y": {"type": "integer"},
            "end_x": {"type": "integer"},
            "end_y": {"type": "integer"},
            "duration_ms": {"type": "integer"},
            "steps": {"type": "integer"},
        },
        "required": ["kind", "start_x", "start_y", "end_x", "end_y"],
    }

    def motion_preview(kind: str, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int | None = None, steps: int = 16) -> dict[str, Any]:
        if not services.safety.check("motion_preview"):
            return error("motion_preview", "blocked by safety gate")
        result = services.executor.motion_preview(kind, (start_x, start_y), (end_x, end_y), duration_ms=duration_ms, steps=steps)
        response = ok("motion_preview", input_payload("motion_preview", result["ok"], result["detail"], {
            "kind": kind,
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "duration_ms": duration_ms or 180,
            "steps": steps,
            "phase": result["phase"],
            "action": result["action"],
            "path": result["path"],
            "metadata": result["metadata"],
            "overlay_state": result["overlay_state"],
        }))
        response["ok"] = result["ok"]
        return response

    registry.register(ToolSpec(
        name="motion_preview",
        kind="input",
        params_schema=motion_schema,
        result_schema=RESULT_SCHEMAS["input"],
        permission="motion_preview",
        executor=motion_preview,
        description="Preview a motion path without changing existing input tool behavior. Use this to inspect planned cursor travel and overlay state before dispatching real actions.",
        param_description="kind/start/end/steps: motion planning inputs. Provide coordinates using start_x/start_y and end_x/end_y.",
        result_description="Standard input envelope with the planned motion path, motion phase, overlay state snapshot, and executor metadata.",
        input_examples=[{"kind": "drag", "start_x": 10, "start_y": 10, "end_x": 100, "end_y": 100}],
        output_examples=MOTION_PREVIEW_OUTPUT_EXAMPLES,
        safety_notes="Planning is gated by the safety service, but the tool is intended to be read-only with respect to existing input implementations.",
        implementation_notes="Calls the orchestrator-facing executor motion preview path and surfaces the generated path plus overlay snapshot.",
    ))
