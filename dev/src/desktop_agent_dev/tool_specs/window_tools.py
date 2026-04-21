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

    registry.register(ToolSpec(name="window_launch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=window_launch, description="启动并聚焦指定窗口或应用，是应用切换与恢复的入口。", param_description="name: 应用名称。", result_description="返回标准输入动作封装，内含启动/聚焦结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="May start external applications.", implementation_notes="Launches via executor.launch_app and reuses the input envelope."))
    registry.register(ToolSpec(name="window_switch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_switch", executor=window_switch, description="切换到指定窗口，适合在多个已打开应用间切换焦点。", param_description="name: 目标窗口名称。", result_description="返回标准输入动作封装，内含切换结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes="Uses fuzzy window matching with foreground restoration."))
    registry.register(ToolSpec(name="window_focus", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_focus", executor=window_focus, description="将焦点聚焦到指定窗口，通常用于后续输入前的准备。", param_description="name: 目标窗口名称。", result_description="返回标准输入动作封装，内含聚焦结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="window_close", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_close", executor=window_close, description="关闭指定窗口，属于高风险操作，应受安全闸控制。", param_description="name: 目标窗口名称。", result_description="返回标准输入动作封装，内含关闭结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="High risk; gated by safety service.", implementation_notes=""))
    registry.register(ToolSpec(name="window_resize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_resize", executor=window_resize, description="调整窗口大小与位置，适合布局校正或多窗口排布。", param_description="name: 目标窗口名称（可选）；width/height/x/y: 目标尺寸与坐标。", result_description="返回标准输入动作封装，记录 resize 结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="window_minimize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_minimize", executor=window_minimize, description="最小化窗口以释放前台焦点。", param_description="name: 目标窗口名称（可选）。", result_description="返回标准输入动作封装，记录 minimize 结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="window_maximize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_maximize", executor=window_maximize, description="将窗口最大化以便进行大范围感知或操作。", param_description="name: 目标窗口名称（可选）。", result_description="返回标准输入动作封装，记录 maximize 结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes=""))
    registry.register(ToolSpec(name="window_restore", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_restore", executor=window_restore, description="从最小化或最大化状态恢复窗口。", param_description="name: 目标窗口名称（可选）。", result_description="返回标准输入动作封装，记录 restore 结果。", input_examples=[{"name": "main"}], output_examples=[], safety_notes="", implementation_notes=""))
