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

    registry.register(ToolSpec(name="window_launch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=window_launch, description="Launch an application window. Use this when the workflow starts from a named desktop app.\n\nParameters: name identifies the app or window to launch.\nReturns: standard input envelope with launch and focus details.\nSafety: may start external applications; gated by the safety service.\nExamples: {\"name\": \"main\"}.", param_description="name: app or window to launch.", result_description="Standard input envelope with launch and focus details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="May start external applications; gated by the safety service.", implementation_notes="Launches via the executor and reuses the input envelope."))
    registry.register(ToolSpec(name="window_switch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_switch", executor=window_switch, description="Switch to an already open window. Use this to move foreground focus between running apps or documents.\n\nParameters: name identifies the target window.\nReturns: standard input envelope with switch details. The payload exposes the prior active window, the current active window, their handles when available, and the backend match mode so clients can verify the switch happened in the intended context.\nSafety: confirm the target window before switching.\nExamples: {\"name\": \"main\"}.", param_description="name: target window.", result_description="Standard input envelope with switch details. Payload includes target_window, previous_window, previous_handle, current_window, current_handle, matched_by, and backend_response.", input_examples=[{"name": "main"}], output_examples=[{"ok": True, "tool": "window_switch", "message": "ok", "data": {"action": "window_switch", "ok": True, "detail": "Switched to ... Sublime Text window.", "payload": {"name": "Sublime Text", "target_window": "Sublime Text", "previous_window": "Codex", "previous_handle": 12345, "current_window": "C:\\Users\\lenovo\\Desktop\\prompt.txt - Sublime Text", "current_handle": 67890, "matched_by": "name", "backend_response": "Switched to ... Sublime Text window."}}}], safety_notes="Confirm the target window before switching.", implementation_notes="Uses fuzzy matching with foreground restoration."))
    registry.register(ToolSpec(name="window_focus", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_focus", executor=window_focus, description="Bring a window into focus. Use this before typing or shortcut actions when the intended target is not currently active.\n\nParameters: name identifies the target window.\nReturns: standard input envelope with focus details.\nSafety: use only when you need to make a specific window the foreground target.\nExamples: {\"name\": \"main\"}.", param_description="name: target window.", result_description="Standard input envelope with focus details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Use only when you need to make a specific window the foreground target.", implementation_notes="Delegates to the executor focus path."))
    registry.register(ToolSpec(name="window_close", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_close", executor=window_close, description="Close a target window or application. This is a high-risk command and should only be used when the user intent is explicit.\n\nParameters: name identifies the window to close.\nReturns: standard input envelope with close details.\nSafety: high risk; gated by the safety service.\nExamples: {\"name\": \"main\"}.", param_description="name: window to close.", result_description="Standard input envelope with close details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="High risk; gated by the safety service.", implementation_notes="Delegates to the executor close path."))
    registry.register(ToolSpec(name="window_resize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_resize", executor=window_resize, description="Resize and reposition a window. Use this for layout adjustments or multi-window workflows.\n\nParameters: name is optional; width and height set the size; x and y set the position.\nReturns: standard input envelope with resize details.\nSafety: verify the target window remains usable after resizing.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window; width/height/x/y: desired geometry.", result_description="Standard input envelope with resize details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Verify the target window remains usable after resizing.", implementation_notes="Delegates to the executor resize path."))
    registry.register(ToolSpec(name="window_minimize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_minimize", executor=window_minimize, description="Minimize a window. Use this to clear the foreground without closing the app.\n\nParameters: name is optional and identifies the window to minimize.\nReturns: standard input envelope with minimize details.\nSafety: only use when minimizing will not interrupt active work.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with minimize details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Only use when minimizing will not interrupt active work.", implementation_notes="Delegates to the executor minimize path."))
    registry.register(ToolSpec(name="window_maximize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_maximize", executor=window_maximize, description="Maximize a window. Use this when you need more visible workspace for inspection or editing.\n\nParameters: name is optional and identifies the window to maximize.\nReturns: standard input envelope with maximize details.\nSafety: may change layout expectations for coordinate-based actions.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with maximize details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="May change layout expectations for coordinate-based actions.", implementation_notes="Delegates to the executor maximize path."))
    registry.register(ToolSpec(name="window_restore", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_restore", executor=window_restore, description="Restore a window to its normal state. Use this after minimizing or maximizing when you want to return to standard interaction posture.\n\nParameters: name is optional and identifies the window to restore.\nReturns: standard input envelope with restore details.\nSafety: restore before the next coordinate-sensitive action if the layout changed.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with restore details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Restore before the next coordinate-sensitive action if the layout changed.", implementation_notes="Delegates to the executor restore path."))
