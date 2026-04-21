from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_window_tools(registry: ToolRegistry, services: Any) -> None:
    def window_launch(name: str) -> dict[str, Any]:
        if not services.safety.check("window_launch"):
            return error("window_launch", "blocked by safety gate")
        result = services.executor.launch_app(name)
        return ok("window_launch", input_payload(result.tool or "window_launch", result.ok, result.detail, result.payload))

    def window_switch(name: str) -> dict[str, Any]:
        if not services.safety.check("window_switch"):
            return error("window_switch", "blocked by safety gate")
        result = services.executor.switch_window(name)
        return ok("window_switch", input_payload(result.tool or "window_switch", result.ok, result.detail, result.payload))

    def window_focus(name: str) -> dict[str, Any]:
        if not services.safety.check("window_focus"):
            return error("window_focus", "blocked by safety gate")
        result = services.executor.focus_window(name)
        return ok("window_focus", input_payload(result.tool or "window_focus", result.ok, result.detail, result.payload))

    def window_close(name: str) -> dict[str, Any]:
        if not services.safety.check("window_close"):
            return error("window_close", "blocked by safety gate")
        result = services.executor.close_window(name)
        return ok("window_close", input_payload(result.tool or "window_close", result.ok, result.detail, result.payload))

    def window_resize(name: str | None = None, width: int | None = None, height: int | None = None, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_resize"):
            return error("window_resize", "blocked by safety gate")
        result = services.executor.resize_window(name=name, width=width, height=height, x=x, y=y)
        return ok("window_resize", input_payload(result.tool or "window_resize", result.ok, result.detail, result.payload))

    def window_minimize(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_minimize"):
            return error("window_minimize", "blocked by safety gate")
        result = services.executor.minimize_window(name)
        return ok("window_minimize", input_payload(result.tool or "window_minimize", result.ok, result.detail, result.payload))

    def window_maximize(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_maximize"):
            return error("window_maximize", "blocked by safety gate")
        result = services.executor.maximize_window(name)
        return ok("window_maximize", input_payload(result.tool or "window_maximize", result.ok, result.detail, result.payload))

    def window_restore(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_restore"):
            return error("window_restore", "blocked by safety gate")
        result = services.executor.restore_window(name)
        return ok("window_restore", input_payload(result.tool or "window_restore", result.ok, result.detail, result.payload))

    specs = [
        ("window_launch", "launch_app", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, window_launch, "启动并聚焦窗口/应用。"),
        ("window_switch", "window_switch", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, window_switch, "切换到指定窗口。"),
        ("window_focus", "window_focus", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, window_focus, "聚焦指定窗口。"),
        ("window_close", "window_close", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, window_close, "关闭指定窗口。"),
        ("window_resize", "window_resize", {"type": "object", "properties": {"name": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": []}, window_resize, "调整窗口大小与位置。"),
        ("window_minimize", "window_minimize", {"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, window_minimize, "最小化窗口。"),
        ("window_maximize", "window_maximize", {"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, window_maximize, "最大化窗口。"),
        ("window_restore", "window_restore", {"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, window_restore, "恢复窗口。"),
    ]
    for name, permission, params_schema, executor, description in specs:
        registry.register(ToolSpec(name=name, kind="window", params_schema=params_schema, result_schema=RESULT_SCHEMAS["input"], permission=permission, executor=executor, description=description, examples=[{"name": "main"}]))
