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
            "trail": [[10, 10], [100, 100]],
            "metadata": {},
        },
        "error": None,
    }
]


def register_overlay_tools(registry: ToolRegistry, services: Any) -> None:
    def overlay_state() -> dict[str, Any]:
        snapshot = services.executor._overlay_renderer.snapshot()
        return ok(
            "overlay_state",
            {
                "visible": snapshot.visible,
                "cursor_x": snapshot.cursor_x,
                "cursor_y": snapshot.cursor_y,
                "trail": [list(point) for point in snapshot.trail],
                "metadata": snapshot.metadata,
            },
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
            result_description="Read-only overlay snapshot with visibility, cursor position, trail, and metadata.",
            input_examples=[{}],
            output_examples=OVERLAY_STATE_OUTPUT_EXAMPLES,
            safety_notes="Read-only; no desktop side effects.",
            implementation_notes="Reads the overlay renderer snapshot exposed through the executor and returns normalized state.",
        )
    )
