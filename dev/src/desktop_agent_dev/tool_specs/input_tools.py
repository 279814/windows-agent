from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


INPUT_EXAMPLES = {
    "input_click": [{"x": 100, "y": 200}, {"x": 100, "y": 200, "button": "right", "clicks": 2}],
    "input_move": [{"x": 100, "y": 200}],
    "input_drag": [{"start_x": 10, "start_y": 10, "end_x": 100, "end_y": 100}],
    "input_type": [{"text": "hello"}, {"text": "hello", "press_enter": True, "clear": True}],
    "input_multi_select": [{"coordinates": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]}],
    "input_multi_edit": [{"edits": [{"x": 1, "y": 2, "text": "a"}, {"x": 3, "y": 4, "text": "b"}]}],
    "input_shortcut": [{"keys": "ctrl+s"}],
    "input_scroll": [{"direction": "down"}],
    "input_launch_app": [{"name": "calc"}],
}


def register_input_tools(registry: ToolRegistry, services: Any) -> None:
    def input_click(x: int, y: int, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        if not services.safety.check("click"):
            return error("input_click", "blocked by safety gate")
        result = services.executor.click(x, y, button=button, clicks=clicks)
        return ok("input_click", input_payload(result.tool or "input_click", result.ok, result.detail, result.payload))

    def input_move(x: int, y: int) -> dict[str, Any]:
        if not services.safety.check("move"):
            return error("input_move", "blocked by safety gate")
        result = services.executor.move(x, y)
        return ok("input_move", input_payload(result.tool or "input_move", result.ok, result.detail, result.payload))

    def input_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> dict[str, Any]:
        if not services.safety.check("drag"):
            return error("input_drag", "blocked by safety gate")
        result = services.executor.drag((start_x, start_y), (end_x, end_y))
        return ok("input_drag", input_payload(result.tool or "input_drag", result.ok, result.detail, result.payload))

    def input_type(text: str, press_enter: bool = False, clear: bool = False, caret_position: str = "idle") -> dict[str, Any]:
        if not services.safety.check("type"):
            return error("input_type", "blocked by safety gate")
        result = services.executor.type_text(text, press_enter=press_enter, clear=clear, caret_position=caret_position)
        return ok("input_type", input_payload(result.tool or "input_type", result.ok, result.detail, result.payload))

    def input_multi_select(coordinates: list[dict[str, int]], press_ctrl: bool = False) -> dict[str, Any]:
        if not services.safety.check("multi_select"):
            return error("input_multi_select", "blocked by safety gate")
        pairs = [(item["x"], item["y"]) for item in coordinates]
        result = services.executor.multi_select(pairs, press_ctrl=press_ctrl)
        return ok("input_multi_select", input_payload(result.tool or "input_multi_select", result.ok, result.detail, result.payload))

    def input_multi_edit(edits: list[dict[str, Any]]) -> dict[str, Any]:
        if not services.safety.check("multi_edit"):
            return error("input_multi_edit", "blocked by safety gate")
        normalized = [(int(item["x"]), int(item["y"]), str(item["text"])) for item in edits]
        result = services.executor.multi_edit(normalized)
        return ok("input_multi_edit", input_payload(result.tool or "input_multi_edit", result.ok, result.detail, result.payload))

    def input_shortcut(keys: str) -> dict[str, Any]:
        if not services.safety.check("shortcut"):
            return error("input_shortcut", "blocked by safety gate")
        result = services.executor.shortcut(keys)
        return ok("input_shortcut", input_payload(result.tool or "input_shortcut", result.ok, result.detail, result.payload))

    def input_scroll(direction: str, amount: int = 1) -> dict[str, Any]:
        if not services.safety.check("scroll"):
            return error("input_scroll", "blocked by safety gate")
        result = services.executor.scroll(direction, amount=amount)
        return ok("input_scroll", input_payload(result.tool or "input_scroll", result.ok, result.detail, result.payload))

    def input_launch_app(name: str) -> dict[str, Any]:
        if not services.safety.check("launch_app"):
            return error("input_launch_app", "blocked by safety gate")
        result = services.executor.launch_app(name)
        return ok("input_launch_app", input_payload(result.tool or "input_launch_app", result.ok, result.detail, result.payload))

    specs = [
        ("input_click", "click", {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "clicks": {"type": "integer", "default": 1}}, "required": ["x", "y"]}, input_click, "点击屏幕坐标。"),
        ("input_move", "move", {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}, input_move, "移动鼠标到指定坐标。"),
        ("input_drag", "drag", {"type": "object", "properties": {"start_x": {"type": "integer"}, "start_y": {"type": "integer"}, "end_x": {"type": "integer"}, "end_y": {"type": "integer"}}, "required": ["start_x", "start_y", "end_x", "end_y"]}, input_drag, "拖拽鼠标。"),
        ("input_type", "type", {"type": "object", "properties": {"text": {"type": "string"}, "press_enter": {"type": "boolean", "default": False}, "clear": {"type": "boolean", "default": False}, "caret_position": {"type": "string", "default": "idle"}}, "required": ["text"]}, input_type, "输入文本。"),
        ("input_multi_select", "multi_select", {"type": "object", "properties": {"coordinates": {"type": "array"}, "press_ctrl": {"type": "boolean", "default": False}}, "required": ["coordinates"]}, input_multi_select, "多点选择。"),
        ("input_multi_edit", "multi_edit", {"type": "object", "properties": {"edits": {"type": "array"}}, "required": ["edits"]}, input_multi_edit, "多点编辑。"),
        ("input_shortcut", "shortcut", {"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]}, input_shortcut, "发送快捷键。"),
        ("input_scroll", "scroll", {"type": "object", "properties": {"direction": {"type": "string"}, "amount": {"type": "integer", "default": 1}}, "required": ["direction"]}, input_scroll, "滚动。"),
        ("input_launch_app", "launch_app", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, input_launch_app, "启动应用。"),
    ]
    for name, permission, params_schema, executor, description in specs:
        registry.register(ToolSpec(name=name, kind="input", params_schema=params_schema, result_schema=RESULT_SCHEMAS["input"], permission=permission, executor=executor, description=description, examples=INPUT_EXAMPLES.get(name, [])))
