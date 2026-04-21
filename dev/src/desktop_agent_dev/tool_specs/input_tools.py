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

    registry.register(ToolSpec(name="input_click", kind="input", params_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "clicks": {"type": "integer", "default": 1}}, "required": ["x", "y"]}, result_schema=RESULT_SCHEMAS["input"], permission="click", executor=input_click, description="点击屏幕坐标，支持左/中/右键与双击。建议在执行前后都做一次桌面观察验证焦点变化。", param_description="x/y: 目标屏幕坐标；button: 鼠标按键；clicks: 点击次数。", result_description="返回标准输入动作封装，内含 action/ok/detail/payload。", input_examples=INPUT_EXAMPLES.get("input_click", []), output_examples=[{"ok": True, "tool": "input_click", "data": {"action": "click", "ok": True, "detail": "clicked", "payload": {}}}], safety_notes="UIA-first with coordinate fallback.", implementation_notes="Clicks are immediate and may need post-action verification."))
    registry.register(ToolSpec(name="input_move", kind="input", params_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}, result_schema=RESULT_SCHEMAS["input"], permission="move", executor=input_move, description="移动鼠标到指定坐标，用于悬停、预热或拖拽起点定位。", param_description="x/y: 鼠标目标坐标。", result_description="返回标准输入动作封装，记录 move 结果。", input_examples=INPUT_EXAMPLES.get("input_move", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_drag", kind="input", params_schema={"type": "object", "properties": {"start_x": {"type": "integer"}, "start_y": {"type": "integer"}, "end_x": {"type": "integer"}, "end_y": {"type": "integer"}}, "required": ["start_x", "start_y", "end_x", "end_y"]}, result_schema=RESULT_SCHEMAS["input"], permission="drag", executor=input_drag, description="拖拽鼠标，适合重排、框选或窗口移动。执行后必须验证目标位置是否真实变化。", param_description="start_x/start_y: 起点；end_x/end_y: 终点。", result_description="返回标准输入动作封装，记录 drag 结果。", input_examples=INPUT_EXAMPLES.get("input_drag", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_type", kind="input", params_schema={"type": "object", "properties": {"text": {"type": "string"}, "press_enter": {"type": "boolean", "default": False}, "clear": {"type": "boolean", "default": False}, "caret_position": {"type": "string", "default": "idle"}}, "required": ["text"]}, result_schema=RESULT_SCHEMAS["input"], permission="type", executor=input_type, description="输入文本到当前焦点控件，支持清空、回车提交和光标位置提示。遇到 IME 时应先切换到英文输入模式。", param_description="text: 要输入的文本；press_enter: 是否回车；clear: 是否先清空；caret_position: start/end/idle。", result_description="返回标准输入动作封装，记录 type 结果。", input_examples=INPUT_EXAMPLES.get("input_type", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_multi_select", kind="input", params_schema={"type": "object", "properties": {"coordinates": {"type": "array"}, "press_ctrl": {"type": "boolean", "default": False}}, "required": ["coordinates"]}, result_schema=RESULT_SCHEMAS["input"], permission="multi_select", executor=input_multi_select, description="按坐标进行多点选择，常用于文件列表、复选框或批量操作。", param_description="coordinates: 依次点击的坐标数组；press_ctrl: 是否按住 Ctrl。", result_description="返回标准输入动作封装，记录 multi_select 结果。", input_examples=INPUT_EXAMPLES.get("input_multi_select", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_multi_edit", kind="input", params_schema={"type": "object", "properties": {"edits": {"type": "array"}}, "required": ["edits"]}, result_schema=RESULT_SCHEMAS["input"], permission="multi_edit", executor=input_multi_edit, description="在多个输入位置同时写入文本，适合表单批量填写。", param_description="edits: [{x, y, text}, ...] 的编辑数组。", result_description="返回标准输入动作封装，记录 multi_edit 结果。", input_examples=INPUT_EXAMPLES.get("input_multi_edit", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_shortcut", kind="input", params_schema={"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]}, result_schema=RESULT_SCHEMAS["input"], permission="shortcut", executor=input_shortcut, description="发送快捷键组合，例如 ctrl+s、alt+tab 或 win+r。建议在前后观察窗口状态变化。", param_description="keys: 以 + 分隔的组合键。", result_description="返回标准输入动作封装，记录 shortcut 结果。", input_examples=INPUT_EXAMPLES.get("input_shortcut", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_scroll", kind="input", params_schema={"type": "object", "properties": {"direction": {"type": "string"}, "amount": {"type": "integer", "default": 1}}, "required": ["direction"]}, result_schema=RESULT_SCHEMAS["input"], permission="scroll", executor=input_scroll, description="在屏幕或目标区域执行滚动。", param_description="direction: up/down/left/right；amount: 滚动次数。", result_description="返回标准输入动作封装，记录 scroll 结果。", input_examples=INPUT_EXAMPLES.get("input_scroll", []), output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="input_launch_app", kind="input", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=input_launch_app, description="启动应用并将其置于可交互状态。", param_description="name: 应用名称或模糊匹配名称。", result_description="返回标准输入动作封装，记录 launch_app 结果。", input_examples=INPUT_EXAMPLES.get("input_launch_app", []), output_examples=[], safety_notes="", implementation_notes=""))
