from __future__ import annotations

from typing import Any

from ..schemas import error, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


OVERLAY_STATE_OUTPUT_EXAMPLES = [
    {
        "ok": True,
        "tool": "overlay_state",
        "message": "ok",
        "data": {
            "visible": False,
            "cursor_x": 100,
            "cursor_y": 100,
            "cursor_color": "#ff0000",
            "user_cursor_color": "#3b82f6",
            "trail": [[10, 10], [100, 100]],
            "transition_state": "idle",
            "transition_reason": None,
            "metadata": {},
        },
        "error": None,
    }
]


def register_overlay_tools(registry: ToolRegistry, services: Any) -> None:
    def overlay_state() -> dict[str, Any]:
        snapshot = services.executor._overlay_renderer.snapshot()
        motion_scheduler = getattr(services.executor, "_motion_scheduler", None)
        motion_state = getattr(motion_scheduler, "cursor_state", None) if motion_scheduler is not None else None
        payload: dict[str, Any] = {
            "visible": snapshot.visible,
            "cursor_x": snapshot.cursor_x,
            "cursor_y": snapshot.cursor_y,
            "cursor_color": snapshot.cursor_color,
            "user_cursor_color": snapshot.user_cursor_color,
            "trail": [list(point) for point in snapshot.trail],
            "click_ripples": snapshot.click_ripples,
            "drag_active": snapshot.drag_active,
            "drag_start": snapshot.drag_start,
            "display_id": snapshot.display_id,
            "scale_factor": snapshot.scale_factor,
            "monitor_bounds": snapshot.monitor_bounds,
            "transition_state": snapshot.transition_state,
            "transition_reason": snapshot.transition_reason,
            "metadata": snapshot.metadata,
        }
        if motion_state is not None:
            payload["motion_state"] = motion_state.snapshot()
        return ok(
            "overlay_state",
            payload,
        )

    registry.register(
        ToolSpec(
            name="overlay_state",
            kind="snapshot",
            params_schema={"type": "object", "properties": {}, "required": []},
            result_schema=RESULT_SCHEMAS["default"],
            permission=None,
            executor=overlay_state,
            description="Read the current dev overlay state, including the latest virtual cursor position and trail, without mutating existing tool implementations.",
            param_description="No parameters. Returns the current overlay snapshot.",
            result_description="Read-only overlay snapshot with visibility, cursor position, trail, metadata, and optional motion-state data.",
            input_examples=[{}],
            output_examples=OVERLAY_STATE_OUTPUT_EXAMPLES,
            safety_notes="Read-only; no desktop side effects.",
            implementation_notes="Reads the overlay renderer snapshot exposed through the executor and returns normalized state. This is one of the phase1 focus tools for virtual cursor inspection.",
        )
    )
