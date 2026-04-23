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
            "kind": {"type": "string", "description": "Trajectory model hint such as move, drag, hover, or click."},
            "start_x": {"type": "integer", "description": "Starting x coordinate."},
            "start_y": {"type": "integer", "description": "Starting y coordinate."},
            "end_x": {"type": "integer", "description": "Ending x coordinate."},
            "end_y": {"type": "integer", "description": "Ending y coordinate."},
            "duration_ms": {"type": "integer", "description": "Overall motion duration."},
            "steps": {"type": "integer", "description": "Number of points used to sample the path."},
            "hover_ms": {"type": "integer", "description": "Hover dwell before or during the motion path."},
            "jitter_px": {"type": "integer", "description": "Maximum humanization jitter in pixels."},
            "accel": {"type": "number", "description": "Acceleration shaping factor for the leading part of the motion."},
            "decel": {"type": "number", "description": "Deceleration shaping factor for the trailing part of the motion."},
        },
        "required": ["kind", "start_x", "start_y", "end_x", "end_y"],
        "additionalProperties": False,
    }

    def motion_preview(kind: str, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int | None = None, steps: int = 16, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, task_id: str | None = None) -> dict[str, Any]:
        if not services.safety.check("motion_preview"):
            return error("motion_preview", "blocked by safety gate")
        try:
            result = services.executor.motion_preview(kind, (start_x, start_y), (end_x, end_y), duration_ms=duration_ms, steps=steps, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel, task_id=task_id)
        except TypeError:
            result = services.executor.motion_preview(kind, (start_x, start_y), (end_x, end_y), duration_ms=duration_ms, steps=steps)
        response = ok("motion_preview", input_payload("motion_preview", result["ok"], result["detail"], {
            "kind": kind,
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "duration_ms": duration_ms or 180,
            "steps": steps,
            "hover_ms": hover_ms,
            "jitter_px": jitter_px,
            "accel": accel,
            "decel": decel,
            "phase": result["phase"],
            "action": result["action"],
            "path": result["path"],
            "metadata": result["metadata"],
            "overlay_state": result["overlay_state"],
            "task_state": result.get("task_state"),
        }))
        response["ok"] = result["ok"]
        return response

    def motion_execute(kind: str, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int | None = None, steps: int = 16, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, task_id: str | None = None) -> dict[str, Any]:
        if not services.safety.check("motion_execute"):
            return error("motion_execute", "blocked by safety gate")
        try:
            result = services.executor.motion_execute(kind, (start_x, start_y), (end_x, end_y), duration_ms=duration_ms, steps=steps, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel, task_id=task_id)
        except TypeError:
            result = services.executor.motion_execute(kind, (start_x, start_y), (end_x, end_y), duration_ms=duration_ms, steps=steps)
        response = ok("motion_execute", input_payload("motion_execute", result["ok"], result["detail"], {
            "kind": kind,
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "duration_ms": duration_ms or 180,
            "steps": steps,
            "hover_ms": hover_ms,
            "jitter_px": jitter_px,
            "accel": accel,
            "decel": decel,
            "phase": result["phase"],
            "action": result["action"],
            "path": result["path"],
            "metadata": result["metadata"],
            "overlay_state": result.get("overlay_state"),
            "task_state": result.get("task_state"),
        }))
        response["ok"] = result["ok"]
        return response

    registry.register(ToolSpec(
        name="motion_preview",
        kind="motion",
        params_schema=motion_schema,
        result_schema=RESULT_SCHEMAS["input"],
        permission="motion_preview",
        executor=motion_preview,
        description="Preview a motion path without changing existing cursor behavior. Use this to inspect planned cursor travel and overlay state before dispatching real actions. Supports humanized trajectory controls including hover_ms, jitter_px, accel, and decel for realistic mouse shaping.",
        param_description="kind/start/end/steps/hover_ms/jitter_px/accel/decel: motion planning inputs. Provide coordinates using start_x/start_y and end_x/end_y. Optional hover_ms adds a natural dwell, jitter_px adds humanization noise, and accel/decel shape the motion envelope.",
        result_description="Standard motion envelope with the planned path, motion phase, overlay state snapshot, and executor metadata, including humanized trajectory settings when provided.",
        input_examples=[{"kind": "drag", "start_x": 10, "start_y": 10, "end_x": 100, "end_y": 100}],
        output_examples=MOTION_PREVIEW_OUTPUT_EXAMPLES,
        safety_notes="Planning is gated by the safety service, but the tool is intended to be read-only with respect to existing input implementations.",
        implementation_notes="Calls the orchestrator-facing executor motion preview path and surfaces the generated path plus overlay snapshot. This is one of the phase1 focus tools for cursor planning.",
    ))
