from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..schemas import ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


DESKTOP_EXAMPLES = [
    {"with_screenshot": False},
    {"with_screenshot": True},
]


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
            params_schema={
                "type": "object",
                "properties": {"with_screenshot": {"type": "boolean", "default": False}},
                "required": [],
            },
            result_schema=RESULT_SCHEMAS["default"],
            permission=None,
            executor=desktop_snapshot,
            description="读取桌面窗口状态、UIA 树与可选截图元数据。",
            examples=DESKTOP_EXAMPLES,
        )
    )
