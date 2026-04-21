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
            description="读取桌面窗口状态、UIA 树与可选截图元数据。用于观察当前活动窗口、窗口列表、光标位置和快照上下文，是执行动作前的默认第一步。",
            param_description="with_screenshot: 是否在快照中附加截图（默认 false）。",
            result_description="返回活动窗口、窗口列表、光标位置、树节点和快照元数据；若启用截图则附带 screenshot 相关信息。",
            input_examples=DESKTOP_EXAMPLES,
            output_examples=[{"ok": True, "tool": "desktop_snapshot", "message": "ok", "data": {"active_window": None, "windows": [], "cursor": [0, 0], "tree_nodes": [], "metadata": {}}}],
            safety_notes="只读，不执行桌面副作用。",
            implementation_notes="通过 perception 层聚合窗口、树节点与可选截图。",
        )
    )
