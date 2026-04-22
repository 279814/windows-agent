from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from PIL import Image

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
                "cursor": {"type": ["array", "null"]},
                "tree_nodes": {"type": "array"},
                "metadata": {"type": "object"},
                "screenshot_path": {"type": ["string", "null"]},
                "screenshot_id": {"type": ["string", "null"]},
                "screenshot_handle": {"type": ["string", "null"]},
                "has_screenshot": {"type": "boolean"},
                "screenshot_bytes": {"type": "integer"},
            },
        },
        "error": {"type": ["object", "null"]},
    },
    "required": ["ok", "tool"],
}


def register_desktop_tools(registry: ToolRegistry, services: Any) -> None:
    def desktop_snapshot(with_screenshot: bool = False) -> dict[str, Any]:
        snapshot = services.perception.snapshot(with_screenshot=with_screenshot)
        screenshot_path = snapshot.screenshot_path
        if with_screenshot and snapshot.screenshot:
            output_dir = Path(__file__).resolve().parents[3] / "tmp"
            output_dir.mkdir(parents=True, exist_ok=True)
            with Image.open(BytesIO(snapshot.screenshot)) as image:
                png_image = image.convert("RGBA")
                with NamedTemporaryFile(delete=False, suffix=".png", prefix="desktop-snapshot-", dir=output_dir) as tmp_file:
                    png_image.save(tmp_file, format="PNG")
                    tmp_file.flush()
                    screenshot_path = tmp_file.name
        screenshot_id = screenshot_path
        screenshot_handle = screenshot_path
        data = {
            "active_window": None if snapshot.active_window is None else asdict(snapshot.active_window),
            "windows": [asdict(window) for window in snapshot.windows],
            "cursor": snapshot.cursor,
            "tree_nodes": [asdict(node) for node in snapshot.tree_nodes],
            "metadata": {**snapshot.metadata, "screenshot_path": screenshot_path, "screenshot_id": screenshot_id, "screenshot_handle": screenshot_handle},
            "screenshot_path": screenshot_path,
            "screenshot_id": screenshot_id,
            "screenshot_handle": screenshot_handle,
            "has_screenshot": snapshot.screenshot is not None,
            "screenshot_bytes": len(snapshot.screenshot or b""),
        }
        return {
            "ok": True,
            "tool": "desktop_snapshot",
            "message": "ok",
            "data": data,
            "error": None,
        }

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
                "When with_screenshot is enabled, the tool also persists the PNG screenshot to dev/tmp and returns screenshot_path, screenshot_id, and screenshot_handle for direct verification. Current handle is the same value as path, so it should not be treated as a different resource type. The windows list attempts to include visible UI context beyond the active window, including currently visible top-level windows and minimized/background context when exposed by the backend. "
                "Best for observe-first workflows, pre-action verification, and understanding the current surface before any input or window change.\n\n"
                "Parameters: with_screenshot controls whether a screenshot is attached to the snapshot.\n"
                "Returns: a normalized observation payload containing active_window, windows, cursor, tree_nodes, metadata, screenshot_path, screenshot_id, screenshot_handle, has_screenshot, screenshot_bytes, and error.\n"
                "Safety: read-only; performs no desktop side effects.\n"
                "Implementation: aggregates window, tree, and optional screenshot data through the perception layer and writes screenshot artifacts into dev/tmp.\n"
                "Examples: {\"with_screenshot\": false}, {\"with_screenshot\": true}."
            ),
            param_description="with_screenshot: attach a screenshot to the snapshot payload when true; also returns a dev/tmp PNG path and screenshot identifiers.",
            result_description="Returns a normalized observation payload with active_window, windows, cursor, tree_nodes, metadata, screenshot_path, screenshot_id, screenshot_handle, has_screenshot, screenshot_bytes, and error.",
            input_examples=DESKTOP_EXAMPLES,
            output_examples=[{"ok": True, "tool": "desktop_snapshot", "message": "ok", "data": {"active_window": {"name": "Codex", "handle": 12345, "process_id": 67890, "is_visible": True, "bounds": [-11, -11, 2571, 1539], "status": "Status.MAXIMIZED", "source": "windows-mcp"}, "windows": [{"name": "Codex", "handle": 12345, "process_id": 67890, "is_visible": True, "bounds": [-11, -11, 2571, 1539], "status": "Status.MAXIMIZED", "source": "windows-mcp"}, {"name": "Taskbar", "handle": 23456, "process_id": 13579, "is_visible": True, "bounds": [0, 1440, 2560, 1539], "status": "Status.NORMAL", "source": "windows-mcp"}, {"name": "Minimized Window", "handle": 34567, "process_id": 24680, "is_visible": False, "bounds": [0, 0, 800, 600], "status": "Status.MINIMIZED", "source": "windows-mcp"}, {"name": "Other Visible Context", "handle": 45678, "process_id": 11223, "is_visible": True, "bounds": [1200, 100, 2400, 900], "status": "Status.NORMAL", "source": "windows-mcp"}], "cursor": [100, 100], "tree_nodes": [{"name": "Start", "control_type": "Button", "bounds": [10, 1450, 50, 1490], "source": "windows-mcp"}], "metadata": {"source": "windows-mcp", "screenshot_path": "dev/tmp/desktop-snapshot-<timestamp>.png", "screenshot_id": "dev/tmp/desktop-snapshot-<timestamp>.png", "screenshot_handle": "dev/tmp/desktop-snapshot-<timestamp>.png"}, "screenshot_path": "dev/tmp/desktop-snapshot-<timestamp>.png", "screenshot_id": "dev/tmp/desktop-snapshot-<timestamp>.png", "screenshot_handle": "dev/tmp/desktop-snapshot-<timestamp>.png", "has_screenshot": True, "screenshot_bytes": 123456}, "error": None}],
            safety_notes="Read-only; performs no desktop side effects.",
            implementation_notes="Aggregates window, tree, and optional screenshot data through the perception layer, persisting screenshots into dev/tmp as PNG files.",
        )
    )
