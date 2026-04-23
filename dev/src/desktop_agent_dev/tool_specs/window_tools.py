from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_window_tools(registry: ToolRegistry, services: Any) -> None:
    def window_launch(name: str) -> dict[str, Any]:
        if not services.safety.check("window_launch"):
            return error("window_launch", "blocked by safety gate")
        result = services.executor.launch_app(name)
        response = ok("window_launch", input_payload("window_launch", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        if not result.ok:
            response["message"] = result.detail
        return response

    def window_switch(name: str) -> dict[str, Any]:
        if not services.safety.check("window_switch"):
            return error("window_switch", "blocked by safety gate")
        result = services.executor.switch_window(name)
        response = ok("window_switch", input_payload(result.tool or "window_switch", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_focus(name: str) -> dict[str, Any]:
        if not services.safety.check("window_focus"):
            return error("window_focus", "blocked by safety gate")
        result = services.executor.focus_window(name)
        response = ok("window_focus", input_payload(result.tool or "window_focus", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_close(name: str) -> dict[str, Any]:
        if not services.safety.check("window_close"):
            return error("window_close", "blocked by safety gate")
        result = services.executor.close_window(name)
        response = ok("window_close", input_payload(result.tool or "window_close", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_resize(name: str | None = None, width: int | None = None, height: int | None = None, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_resize"):
            return error("window_resize", "blocked by safety gate")
        result = services.executor.resize_window(name=name, width=width, height=height, x=x, y=y)
        response = ok("window_resize", input_payload(result.tool or "window_resize", result.ok, result.detail, result.payload), message="ok" if result.ok else "error")
        response["ok"] = result.ok
        return response

    def window_minimize(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_minimize"):
            return error("window_minimize", "blocked by safety gate")
        result = services.executor.minimize_window(name)
        response = ok("window_minimize", input_payload(result.tool or "window_minimize", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_maximize(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_maximize"):
            return error("window_maximize", "blocked by safety gate")
        result = services.executor.maximize_window(name)
        response = ok("window_maximize", input_payload(result.tool or "window_maximize", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_restore(name: str | None = None) -> dict[str, Any]:
        if not services.safety.check("window_restore"):
            return error("window_restore", "blocked by safety gate")
        result = services.executor.restore_window(name)
        response = ok("window_restore", input_payload(result.tool or "window_restore", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    registry.register(ToolSpec(name="window_launch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=window_launch, description="Launch an application window. Use this when the workflow starts from a named desktop app.\n\nParameters: name identifies the app or window to launch.\nReturns: standard input envelope with launch verification details. The action field is normalized to window_launch even though the executor reuses the app-launch pipeline.\nSafety: may start external applications; gated by the safety service.\nExamples: {\"name\": \"main\"}.", param_description="name: app or window to launch.", result_description="Standard input envelope with launch verification details, including requested target, matched target, detected window name, verification source, verification_status, and backend launch response.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="May start external applications; gated by the safety service.", implementation_notes="Wraps the launch executor and normalizes the action name to window_launch for MCP clients."))
    registry.register(ToolSpec(name="window_switch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_switch", executor=window_switch, description="Switch to an already open window. Use this to move foreground focus between running apps or documents.\n\nParameters: name identifies the target window.\nReturns: standard input envelope with switch details. The payload exposes the prior active window, the current active window, their handles when available, whether the previous window was restored from a minimized state, and the backend match mode so clients can verify the switch happened in the intended context.\nBehavior note: if the source window is minimized, it is restored before the foreground switch so the resulting focus change is visible and consistent.\nBehavior note: use this as part of an observe -> switch -> observe loop so the current foreground target can be verified immediately after the transition.\nSafety: confirm the target window before switching.\nExamples: {\"name\": \"main\"}.", param_description="name: target window.", result_description="Standard input envelope with switch details. Payload includes target_window, previous_window, previous_handle, current_window, current_handle, matched_by, restored_from_minimized, backend_response, backend_response_detail, backend_response_code, and verified. Top-level ok is false when the switch could not be verified.", input_examples=[{"name": "main"}], output_examples=[{"ok": True, "tool": "window_switch", "message": "ok", "data": {"action": "window_switch", "ok": True, "detail": "Switched to ... Sublime Text window.", "payload": {"name": "Sublime Text", "target_window": "Sublime Text", "previous_window": "Codex", "previous_handle": 12345, "current_window": "C:\\Users\\lenovo\\Desktop\\prompt.txt - Sublime Text", "current_handle": 67890, "matched_by": "name", "restored_from_minimized": True, "backend_response": ["Switched to ... Sublime Text window.", 0], "backend_response_detail": "Switched to ... Sublime Text window.", "backend_response_code": 0, "verified": True}}}, {"ok": False, "tool": "window_switch", "message": "Application Main not found.", "data": {"action": "window_switch", "ok": False, "detail": "Application Main not found.", "payload": {"name": "main", "backend_response": ["Application Main not found.", 1], "backend_response_code": 1, "verified": False}}}], safety_notes="Confirm the target window before switching.", implementation_notes="Uses fuzzy matching with foreground restoration and restores minimized sources before switching when needed."))
    registry.register(ToolSpec(name="window_focus", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_focus", executor=window_focus, description="Bring a window into focus. Use this before typing or shortcut actions when the intended target is not currently active.\n\nParameters: name identifies the target window.\nReturns: standard input envelope with focus details.\nSafety: use only when you need to make a specific window the foreground target.\nExamples: {\"name\": \"main\"}.", param_description="name: target window.", result_description="Standard input envelope with focus details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Use only when you need to make a specific window the foreground target.", implementation_notes="Delegates to the executor focus path."))
    registry.register(ToolSpec(name="window_close", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="window_close", executor=window_close, description="Close a window or app. High-risk; use only with explicit user intent. The final result is determined by post-close verification of the desktop state, not just the backend call result. The backend_response field records the primary close-path response, while ok reflects the verified desktop outcome.\n\nBehavior note: verify the requested target window itself, not merely the current foreground app, after the close attempt.\n\nParameters: name: window to close.\nReturns: standard input envelope with close details, close strategy, backend response, exit code, and post-close verification. Outcome values include capability_missing, safety_blocked, execution_failed, execution_succeeded, and success_wm_close_degraded. success_wm_close_degraded means the WM_CLOSE attempt failed but the window was still closed successfully via post-close verification.", param_description="name: window to close.", result_description="Standard input envelope with close details, close strategy, backend response, exit code, and post-close verification. Outcome values include capability_missing, safety_blocked, execution_failed, execution_succeeded, and success_wm_close_degraded. success_wm_close_degraded means the WM_CLOSE attempt failed but the window was still closed successfully via post-close verification.", input_examples=[{"name": "main"}], output_examples=[{"ok": True, "tool": "window_close", "message": "ok", "data": {"action": "window_close", "ok": True, "detail": "Closed.", "payload": {"name": "main", "target_window": "main", "close_strategy": "backend.close_app", "backend_response": ["Closed.", 0], "exit_code": 0, "post_close_verified": True, "outcome": "execution_succeeded"}}}, {"ok": True, "tool": "window_close", "message": "ok", "data": {"action": "window_close", "ok": True, "detail": "Closed main.", "payload": {"name": "main", "target_window": "main", "close_strategy": "backend.close_app", "backend_response": ["Failed to post WM_CLOSE to main.", 1], "exit_code": 0, "post_close_verified": True, "outcome": "success_wm_close_degraded"}}}, {"ok": False, "tool": "window_close", "message": "ok", "data": {"action": "window_close", "ok": False, "detail": "Close verification failed for main.", "payload": {"name": "main", "target_window": "main", "close_strategy": "backend.close_app", "backend_response": ["Failed to post WM_CLOSE to main.", 1], "exit_code": 1, "post_close_verified": False, "outcome": "execution_failed"}}}], safety_notes="High risk; gated by the safety service.", implementation_notes="Delegates to backend close_app() and uses post-close verification to set the final result. Main-path failures that still end in a closed window are reported as success_wm_close_degraded.", backend_method="close_app"))
    registry.register(ToolSpec(name="window_resize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_resize", executor=window_resize, description="Resize and reposition a window. Use this for layout adjustments or multi-window workflows.\n\nParameters: name is optional; width and height set the size; x and y set the position.\nReturns: standard input envelope with resize details plus verification metadata about the target window and backend resize response.\nSafety: verify the target window remains usable after resizing.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window; width/height/x/y: desired geometry.", result_description="Standard input envelope with resize details. Payload includes before/after window snapshots, requested size and position, attempted_restore, reason, backend_response_detail, backend_response_code, and verified.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Verify the target window remains usable after resizing.", implementation_notes="Delegates to the executor resize path and verifies the result against the same window handle when possible."))
    registry.register(ToolSpec(name="window_minimize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_minimize", executor=window_minimize, description="Minimize a window. Use this to clear the foreground without closing the app.\n\nParameters: name is optional and identifies the window to minimize.\nReturns: standard input envelope with minimize details and verification metadata.\nSafety: only use when minimizing will not interrupt active work.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with minimize details. Payload includes before/after window snapshots, active_window_after, verification_mode, target_handle_present_after, backend_response_detail, backend_response_code, and verified. The server treats a handle disappearing from the visible window list as a valid minimize outcome when the target is no longer foreground.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Only use when minimizing will not interrupt active work.", implementation_notes="Delegates to the executor minimize path and verifies against the original window handle to reduce false negatives in duplicate-title scenarios."))
    registry.register(ToolSpec(name="window_maximize", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_maximize", executor=window_maximize, description="Maximize a window. Use this when you need more visible workspace for inspection or editing.\n\nParameters: name is optional and identifies the window to maximize.\nReturns: standard input envelope with maximize details.\nSafety: may change layout expectations for coordinate-based actions.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with maximize details.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="May change layout expectations for coordinate-based actions.", implementation_notes="Delegates to the executor maximize path."))
    registry.register(ToolSpec(name="window_restore", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_restore", executor=window_restore, description="Restore a window to its normal state. Use this after minimizing or maximizing when you want to return to standard interaction posture.\n\nParameters: name is optional and identifies the window to restore.\nReturns: standard input envelope with restore details and verification metadata.\nSafety: restore before the next coordinate-sensitive action if the layout changed.\nExamples: {\"name\": \"main\"}.", param_description="name: optional target window.", result_description="Standard input envelope with restore details. Payload includes before/after window snapshots, backend_response_detail, backend_response_code, and verified.", input_examples=[{"name": "main"}], output_examples=[], safety_notes="Restore before the next coordinate-sensitive action if the layout changed.", implementation_notes="Delegates to the executor restore path and verifies against the same window handle when possible."))
