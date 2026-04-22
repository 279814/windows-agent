from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


INPUT_EXAMPLES = {
    "input_click": [{"x": 100, "y": 200}, {"x": 100, "y": 200, "button": "right", "clicks": 2}],
    "input_move": [{"x": 100, "y": 200}],
    "input_drag": [{"start_x": 10, "start_y": 10, "end_x": 100, "end_y": 100}],
    "input_type": [{"text": "hello"}, {"text": "hello", "press_enter": True, "clear": True}, {"text": "notepad", "clear": False}],
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
        before_snapshot = services.perception.snapshot(with_screenshot=False)
        result = services.executor.type_text(text, press_enter=press_enter, clear=clear, caret_position=caret_position)
        after_snapshot = services.perception.snapshot(with_screenshot=False)

        before_control = before_snapshot.focused_control or {}
        after_control = after_snapshot.focused_control or {}
        before_value = before_control.get("value") or before_control.get("text")
        after_value = after_control.get("value") or after_control.get("text")
        target_control = (result.payload or {}).get("target_control") or before_snapshot.focused_control
        target_value_before = None
        target_value_after = None
        if isinstance(target_control, dict):
            target_value_before = target_control.get("value") or target_control.get("text")
        if isinstance(after_snapshot.focused_control, dict):
            target_value_after = after_snapshot.focused_control.get("value") or after_snapshot.focused_control.get("text")
        value_changed = before_value != after_value
        target_changed = target_value_before != target_value_after if target_value_before is not None else None
        validation = {
            "checked": True,
            "field": "focused_control.value",
            "before_value": before_value,
            "after_value": after_value,
            "changed": value_changed,
            "expected_change": True,
            "passed": (not result.ok) or value_changed,
            "target_control": target_control,
            "target_value_before": target_value_before,
            "target_value_after": target_value_after,
            "target_changed": target_changed,
            "before_control_name": before_control.get("name"),
            "after_control_name": after_control.get("name"),
        }
        payload = {
            **(result.payload or {}),
            "focused_control": after_snapshot.focused_control,
            "validation": validation,
        }
        if after_snapshot.focused_control is None and before_snapshot.focused_control is not None:
            payload["focused_control"] = before_snapshot.focused_control

        return ok(
            "input_type",
            input_payload(
                result.tool or "input_type",
                result.ok,
                result.detail,
                payload,
            ),
        )

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

    registry.register(ToolSpec(name="input_click", kind="input", params_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "clicks": {"type": "integer", "default": 1}}, "required": ["x", "y"]}, result_schema=RESULT_SCHEMAS["input"], permission="click", executor=input_click, description="Click a coordinate. Use this when the target point is already known and you want a direct pointer action.\n\nParameters: x/y set the target coordinate; button picks left, middle, or right; clicks sets the click count.\nReturns: standard input envelope with action, ok, detail, and payload. Payload may include click coordinates, button, click count, and hit-test element information.\nSafety: verify focus before and after the click.\nBehavior note: use this as part of an observe -> click -> observe loop so the updated desktop state can be verified after the action.\nExamples: {\"x\": 100, \"y\": 200}, {\"x\": 100, \"y\": 200, \"button\": \"right\", \"clicks\": 2}.\n\nRuntime note: the element payload may include richer hit-test metadata such as z-order, ancestry depth, bounds, and confidence scoring.", param_description="x/y: target coordinate; button: left, middle, or right; clicks: click count.", result_description="Standard input envelope with action, ok, detail, and payload. Payload may include click coordinates, button, click count, and hit-test element information.", input_examples=INPUT_EXAMPLES.get("input_click", []), output_examples=[{"ok": True, "tool": "input_click", "message": "ok", "data": {"action": "input_click", "ok": True, "detail": "clicked:618,1564:left:1", "payload": {"x": 618, "y": 1564, "button": "left", "clicks": 1, "element": {"type": "Button", "name": "Start", "automation_id": "StartMenuButton", "class_name": "StartMenuButton", "role": "push button", "process_id": 1234, "window_title": "Start", "found": True, "confidence": 0.932, "z_index": 0, "ancestry_depth": 1, "bounds": {"left": 600, "top": 1540, "right": 640, "bottom": 1580}, "source": "tree_state"}}}}], safety_notes="Verify focus before and after the click.", implementation_notes="Delegates to the executor click path.") )
    registry.register(ToolSpec(name="input_move", kind="input", params_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}, result_schema=RESULT_SCHEMAS["input"], permission="move", executor=input_move, description="Move the pointer. Use this for hover prep, target acquisition, or drag origin setup.\n\nParameters: x/y set the pointer destination.\nReturns: standard input envelope with the move result.\nSafety: pointer movement only; no application state change.\nExamples: {\"x\": 100, \"y\": 200}.", param_description="x/y: pointer destination.", result_description="Standard input envelope with the move result.", input_examples=INPUT_EXAMPLES.get("input_move", []), output_examples=[], safety_notes="Pointer movement only; no application state change.", implementation_notes="Delegates to the executor move path.") )
    registry.register(ToolSpec(name="input_drag", kind="input", params_schema={"type": "object", "properties": {"start_x": {"type": "integer"}, "start_y": {"type": "integer"}, "end_x": {"type": "integer"}, "end_y": {"type": "integer"}}, "required": ["start_x", "start_y", "end_x", "end_y"]}, result_schema=RESULT_SCHEMAS["input"], permission="drag", executor=input_drag, description="Drag from one coordinate to another. Use this for selection, reordering, and moving on-screen objects.\n\nParameters: start_x/start_y define the origin; end_x/end_y define the destination.\nReturns: standard input envelope with the drag result.\nSafety: confirm the target actually moved or selected as expected.\nExamples: {\"start_x\": 10, \"start_y\": 10, \"end_x\": 100, \"end_y\": 100}.", param_description="start_x/start_y: drag origin; end_x/end_y: drag destination.", result_description="Standard input envelope with the drag result.", input_examples=INPUT_EXAMPLES.get("input_drag", []), output_examples=[], safety_notes="Confirm the target actually moved or selected as expected.", implementation_notes="Delegates to the executor drag path.") )
    registry.register(ToolSpec(name="input_type", kind="input", params_schema={"type": "object", "properties": {"text": {"type": "string"}, "press_enter": {"type": "boolean", "default": False}, "clear": {"type": "boolean", "default": False}, "caret_position": {"type": "string", "default": "idle"}}, "required": ["text"]}, result_schema=RESULT_SCHEMAS["input"], permission="type", executor=input_type, description="Type text into the focused control. Use this when the target field is active and keyboard input is the intended action.\n\nParameters: text is the content to enter; press_enter submits after typing; clear removes the current value first; caret_position hints the expected cursor state.\nReturns: standard input envelope with the typing result. The payload includes the focused control snapshot and an explicit validation block showing whether the focused value changed after typing.\nSafety: switch IME or keyboard layout before typing into localized controls.\nBehavior note: use this as part of an observe -> type -> observe loop so the updated focused control can be verified after the action. If focus is lost, the tool preserves the prior focused_control snapshot in the payload so clients can see the intended target.\nExamples: {\"text\": \"hello\"}, {\"text\": \"hello\", \"press_enter\": true, \"clear\": true}, {\"text\": \"notepad\", \"clear\": false}.", param_description="text: content to type; press_enter: submit after typing; clear: replace existing value; caret_position: start/end/idle hint.", result_description="Standard input envelope with the typing result. Payload includes the focused_control snapshot and validation details, including before/after value change checks.", input_examples=INPUT_EXAMPLES.get("input_type", []), output_examples=[{"ok": True, "tool": "input_type", "message": "ok", "data": {"action": "type", "ok": True, "detail": "typed:notepad", "payload": {"focused_control": {"name": "notepad", "value": "notepad", "text": "notepad", "control_type": "Edit", "automation_id": "searchBox", "class_name": "TextBox", "role": "text box", "bounds": {"left": 16, "top": 16, "right": 360, "bottom": 44}, "window_title": "搜索", "source": "windows-mcp"}, "validation": {"checked": True, "field": "focused_control.value", "before_value": "", "after_value": "notepad", "changed": True, "expected_change": True, "passed": True}}}, "error": None}], safety_notes="Switch IME or keyboard layout before typing into localized controls.", implementation_notes="Delegates to the executor text-input path and re-snapshots focused control state before and after typing.") )
    registry.register(ToolSpec(name="input_multi_select", kind="input", params_schema={"type": "object", "properties": {"coordinates": {"type": "array"}, "press_ctrl": {"type": "boolean", "default": False}}, "required": ["coordinates"]}, result_schema=RESULT_SCHEMAS["input"], permission="multi_select", executor=input_multi_select, description="Select multiple coordinates in sequence. Use this for list items, grids, and bulk selection flows.\n\nParameters: coordinates is the ordered click list; press_ctrl enables additive selection.\nReturns: standard input envelope with the multi-select result.\nSafety: only use where the target UI supports multi-select behavior.\nExamples: {\"coordinates\": [{\"x\": 1, \"y\": 2}, {\"x\": 3, \"y\": 4}]}.", param_description="coordinates: ordered click list; press_ctrl: hold Ctrl while selecting.", result_description="Standard input envelope with the multi-select result.", input_examples=INPUT_EXAMPLES.get("input_multi_select", []), output_examples=[], safety_notes="Only use where the target UI supports multi-select behavior.", implementation_notes="Converts the coordinate list into executor-friendly pairs.") )
    registry.register(ToolSpec(name="input_multi_edit", kind="input", params_schema={"type": "object", "properties": {"edits": {"type": "array"}}, "required": ["edits"]}, result_schema=RESULT_SCHEMAS["input"], permission="multi_edit", executor=input_multi_edit, description="Write text into multiple targets in one pass. Use this for form filling and repeated field edits.\n\nParameters: edits is an array of {x, y, text} entries.\nReturns: standard input envelope with the multi-edit result.\nSafety: only use on forms or editors that can accept bulk input safely.\nExamples: {\"edits\": [{\"x\": 1, \"y\": 2, \"text\": \"a\"}, {\"x\": 3, \"y\": 4, \"text\": \"b\"}]}.", param_description="edits: array of {x, y, text} write targets.", result_description="Standard input envelope with the multi-edit result.", input_examples=INPUT_EXAMPLES.get("input_multi_edit", []), output_examples=[], safety_notes="Only use on forms or editors that can accept bulk input safely.", implementation_notes="Normalizes the edit tuples before dispatching them to the executor.") )
    registry.register(ToolSpec(name="input_shortcut", kind="input", params_schema={"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]}, result_schema=RESULT_SCHEMAS["input"], permission="shortcut", executor=input_shortcut, description="Send a keyboard shortcut such as Ctrl+S, Alt+Tab, or Win+R. Use this when the active window is already the intended target.\n\nParameters: keys is the shortcut string using plus-separated modifiers and keys.\nReturns: standard input envelope with the shortcut result. The payload makes the execution context observable, including the target window or foreground focus before and after the shortcut, whether focus moved to a different window or remained on the same one, and the backend injection result object returned by the executor.\nSafety: confirm the foreground window before sending the shortcut.\nBehavior note: use this as part of an observe -> shortcut -> observe loop, because the focus can legitimately move and should be verified against the intended target.\nExamples: {\"keys\": \"ctrl+s\"}.", param_description="keys: plus-separated modifier and key combination.", result_description="Standard input envelope with the shortcut result. Payload should include target window / focus movement / injection outcome details so clients can verify the shortcut landed in the expected context.", input_examples=INPUT_EXAMPLES.get("input_shortcut", []), output_examples=[{"ok": True, "tool": "input_shortcut", "message": "ok", "data": {"action": "shortcut", "ok": True, "detail": "shortcut:esc", "payload": {"keys": "esc", "target_window": "Search", "focus_before": "Search", "focus_after": "Codex", "focus_changed": True, "injection_result": {"status": "sent", "method": "SendInput", "scan_code": False}}}}], safety_notes="Confirm the foreground window before sending the shortcut.", implementation_notes="Delegates to the executor shortcut path.") )
    registry.register(ToolSpec(name="input_scroll", kind="input", params_schema={"type": "object", "properties": {"direction": {"type": "string"}, "amount": {"type": "integer", "default": 1}}, "required": ["direction"]}, result_schema=RESULT_SCHEMAS["input"], permission="scroll", executor=input_scroll, description="Scroll the current surface or target region. Use this to page through content or reveal hidden UI.\n\nParameters: direction chooses up, down, left, or right; amount sets the number of scroll steps.\nReturns: standard input envelope with the scroll result.\nSafety: nested scroll containers may absorb the action instead of the viewport.\nExamples: {\"direction\": \"down\"}.", param_description="direction: up/down/left/right; amount: scroll step count.", result_description="Standard input envelope with the scroll result.", input_examples=INPUT_EXAMPLES.get("input_scroll", []), output_examples=[], safety_notes="Nested scroll containers may absorb the action instead of the viewport.", implementation_notes="Delegates to the executor scroll path.") )
    registry.register(ToolSpec(name="input_launch_app", kind="input", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=input_launch_app, description="Launch an application. Use this when the workflow starts from a named desktop app.\n\nParameters: name is the application name or fuzzy match target.\nReturns: standard input envelope with the launch result.\nSafety: may start external applications; the safety gate should approve the action first.\nExamples: {\"name\": \"calc\"}.", param_description="name: application name or fuzzy match target.", result_description="Standard input envelope with the launch result.", input_examples=INPUT_EXAMPLES.get("input_launch_app", []), output_examples=[], safety_notes="May start external applications; the safety gate should approve the action first.", implementation_notes="Delegates to the executor launch path.") )
