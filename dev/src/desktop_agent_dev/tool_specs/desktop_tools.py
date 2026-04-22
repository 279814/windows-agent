from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..schemas import ok
from ..tool_registry import ToolRegistry, ToolSpec


DESKTOP_EXAMPLES = [
    {"with_screenshot": False},
    {"with_screenshot": True},
]

DESKTOP_PARAMS = {
    "type": "object",
    "properties": {
        "with_screenshot": {
            "type": "boolean",
            "default": False,
            "description": "Whether to include a screenshot in the snapshot payload.",
        }
    },
    "required": [],
}

DESKTOP_RESULT = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "tool": {"type": "string"},
        "message": {"type": "string"},
        "data": {
            "type": "object",
            "properties": {
                "active_window": {"type": ["object", "null"]},
                "windows": {"type": "array"},
                "cursor": {"type": "array"},
                "tree_nodes": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        "error": {"type": "object"},
    },
    "required": ["ok", "tool"],
}


def register_desktop_tools(registry: ToolRegistry, services: Any) -> None:
    def desktop_snapshot(with_screenshot: bool = False) -> dict[str, Any]:
        snapshot = services.perception.snapshot(with_screenshot=with_screenshot)
        data = {
            "active_window": None if snapshot.active_window is None else asdict(snapshot.active_window),
            "windows": [asdict(window) for window in snapshot.windows],
            "cursor": snapshot.cursor,
            "tree_nodes": [asdict(node) for node in snapshot.tree_nodes],
            "metadata": snapshot.metadata,
        }
        return ok("desktop_snapshot", data)

    registry.register(
        ToolSpec(
            name="desktop_snapshot",
            kind="snapshot",
            params_schema=DESKTOP_PARAMS,
            result_schema=DESKTOP_RESULT,
            permission=None,
            executor=desktop_snapshot,
            description=(
                "Capture the current desktop state, including the active window, open windows, cursor position, UIA tree, and optional screenshot metadata. "
                "Best for observe-first workflows, pre-action verification, and understanding the current surface before any input or window change.\n\n"
                "Parameters: with_screenshot controls whether a screenshot is attached to the snapshot.\n"
                "Returns: a normalized observation payload containing active_window, windows, cursor, tree_nodes, and metadata.\n"
                "Safety: read-only; performs no desktop side effects.\n"
                "Implementation: aggregates window, tree, and optional screenshot data through the perception layer.\n"
                "Examples: {\"with_screenshot\": false}, {\"with_screenshot\": true}."
            ),
            param_description="with_screenshot: attach a screenshot to the snapshot payload when true.",
            result_description="Returns a normalized observation payload with active_window, windows, cursor, tree_nodes, and metadata.",
            input_examples=DESKTOP_EXAMPLES,
            output_examples=[{"ok": True, "tool": "desktop_snapshot", "message": "ok", "data": {"active_window": None, "windows": [], "cursor": [0, 0], "tree_nodes": [], "metadata": {}}}],
            safety_notes="Read-only; performs no desktop side effects.",
            implementation_notes="Aggregates window, tree, and optional screenshot data through the perception layer.",
        )
    )
