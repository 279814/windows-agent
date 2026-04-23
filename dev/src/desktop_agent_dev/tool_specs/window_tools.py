from __future__ import annotations

from typing import Any

from ..schemas import error, input_payload, ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


WINDOW_LAUNCH_OUTPUT_EXAMPLES = [
    {
        "ok": True,
        "tool": "window_launch",
        "message": "ok",
        "data": {
            "action": "window_launch",
            "ok": True,
            "detail": "launched:calc",
            "payload": {
                "name": "calc",
                "requested_target": "calc",
                "matched_target": "calc.exe",
                "effective_target": "calc.exe",
                "resolved_alias": "calc.exe",
                "backend_response": ["22400\r\n [attempted=direct:calc.exe; verification=name:计算器]", 0, 4968],
                "status": 0,
                "pid": 4968,
                "before_window_count": 8,
                "after_window_count": 9,
                "window_detected": True,
                "detected_window_name": "计算器",
                "verification_source": "name",
                "verification_hint": "计算器",
                "target_matches": True,
                "verification_status": "success",
                "result_code": "OK",
                "warning": None,
            },
        },
        "error": None,
    }
]

WINDOW_SWITCH_OUTPUT_EXAMPLES = [
    {
        "ok": False,
        "tool": "window_switch",
        "message": "ok",
        "data": {
            "action": "window_switch",
            "ok": False,
            "detail": "Switched to *Test.Txt - Notepad window.",
            "payload": {
                "before_target_window": "计算器",
                "before_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "before_status": "NORMAL",
                "before_handle": 4983846,
                "target_window": "test.txt - Notepad",
                "after_window": {
                    "name": "*test.txt - Notepad",
                    "status": "NORMAL",
                    "handle": 526982,
                    "window_title": "*test.txt - Notepad",
                },
                "after_status": "NORMAL",
                "after_handle": 526982,
                "name": "test.txt - Notepad",
                "previous_window": "计算器",
                "previous_handle": 4983846,
                "current_window": "*test.txt - Notepad",
                "current_handle": 526982,
                "matched_by": "name",
                "restored_from_minimized": False,
                "backend_response": ["Switched to *Test.Txt - Notepad window.", 0],
                "backend_response_detail": "Switched to *Test.Txt - Notepad window.",
                "backend_response_code": 0,
                "verified": False,
            },
        },
        "error": None,
    }
]

WINDOW_FOCUS_OUTPUT_EXAMPLES = [
    {
        "ok": True,
        "tool": "window_focus",
        "message": "ok",
        "data": {
            "action": "window_focus",
            "ok": True,
            "detail": "Restored Test.Txt - Notepad from minimized and switched to it.",
            "payload": {
                "before_target_window": "Codex",
                "before_window": {"name": "Codex", "status": "MAXIMIZED", "handle": 198440, "window_title": "Codex"},
                "before_status": "MAXIMIZED",
                "before_handle": 198440,
                "target_window": "test.txt - Notepad",
                "after_window": {
                    "name": "test.txt - Notepad",
                    "status": "NORMAL",
                    "handle": 526982,
                    "window_title": "test.txt - Notepad",
                },
                "after_status": "NORMAL",
                "after_handle": 526982,
                "name": "test.txt - Notepad",
                "previous_window": "Codex",
                "previous_handle": 198440,
                "current_window": "test.txt - Notepad",
                "current_handle": 526982,
                "matched_by": "name",
                "restored_from_minimized": False,
                "backend_response": ["Restored Test.Txt - Notepad from minimized and switched to it.", 0],
                "backend_response_detail": "Restored Test.Txt - Notepad from minimized and switched to it.",
                "backend_response_code": 0,
                "verified": True,
                "strategy": "switch_window",
            },
        },
        "error": None,
    }
]

WINDOW_CLOSE_OUTPUT_EXAMPLES = [
    {
        "ok": False,
        "tool": "window_close",
        "message": "ok",
        "data": {
            "action": "window_close",
            "ok": False,
            "detail": "Failed to post WM_CLOSE to 计算器.",
            "payload": {
                "name": "计算器",
                "target_window": "计算器",
                "close_strategy": "backend.close_app",
                "requested_close_path": "wm_close",
                "backend_response": ["Failed to post WM_CLOSE to 计算器.", 1],
                "exit_code": 1,
                "post_close_verified": False,
                "outcome": "execution_failed",
            },
        },
        "error": None,
    }
]

WINDOW_MAXIMIZE_OUTPUT_EXAMPLES = [
    {
        "ok": False,
        "tool": "window_maximize",
        "message": "ok",
        "data": {
            "action": "window_maximize",
            "ok": False,
            "detail": "Maximize verification failed for 计算器.",
            "payload": {
                "before_target_window": "计算器",
                "before_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "before_status": "NORMAL",
                "before_handle": 4983846,
                "target_window": "计算器",
                "after_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "after_status": "NORMAL",
                "after_handle": 4983846,
                "verified": False,
                "backend_response": ["Maximized 计算器 window.", 0],
                "backend_response_detail": "Maximized 计算器 window.",
                "backend_response_code": 0,
            },
        },
        "error": None,
    }
]

WINDOW_MINIMIZE_OUTPUT_EXAMPLES = [
    {
        "ok": False,
        "tool": "window_minimize",
        "message": "ok",
        "data": {
            "action": "window_minimize",
            "ok": False,
            "detail": "Minimize verification failed for 计算器.",
            "payload": {
                "before_target_window": "计算器",
                "before_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "before_status": "NORMAL",
                "before_handle": 4983846,
                "target_window": "计算器",
                "after_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "after_status": "NORMAL",
                "after_handle": 4983846,
                "verified": False,
                "verification_mode": "unverified",
                "target_handle_present_after": True,
                "active_window_after": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "backend_response": ["计算器 minimized.", 0],
                "backend_response_detail": "计算器 minimized.",
                "backend_response_code": 0,
            },
        },
        "error": None,
    }
]

WINDOW_RESTORE_OUTPUT_EXAMPLES = [
    {
        "ok": True,
        "tool": "window_restore",
        "message": "ok",
        "data": {
            "action": "window_restore",
            "ok": True,
            "detail": "Restored 计算器 window.",
            "payload": {
                "before_target_window": "计算器",
                "before_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "before_status": "NORMAL",
                "before_handle": 4983846,
                "target_window": "计算器",
                "after_window": {"name": "计算器", "status": "NORMAL", "handle": 4983846, "window_title": "计算器"},
                "after_status": "NORMAL",
                "after_handle": 4983846,
                "verified": True,
                "backend_response": ["Restored 计算器 window.", 0],
                "backend_response_detail": "Restored 计算器 window.",
                "backend_response_code": 0,
            },
        },
        "error": None,
    }
]


def register_window_tools(registry: ToolRegistry, services: Any) -> None:
    target_selector_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "handle": {"type": "integer"},
            "pid": {"type": "integer"},
        },
        "required": [],
    }

    def window_launch(name: str) -> dict[str, Any]:
        if not services.safety.check("window_launch"):
            return error("window_launch", "blocked by safety gate")
        result = services.executor.launch_app(name)
        response = ok("window_launch", input_payload("window_launch", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        if not result.ok:
            response["message"] = result.detail
        return response

    def window_switch(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_switch"):
            return error("window_switch", "blocked by safety gate")
        result = services.executor.switch_window(name or "", handle=handle, pid=pid)
        response = ok("window_switch", input_payload(result.tool or "window_switch", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_focus(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_focus"):
            return error("window_focus", "blocked by safety gate")
        result = services.executor.focus_window(name or "", handle=handle, pid=pid)
        response = ok("window_focus", input_payload(result.tool or "window_focus", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_close(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_close"):
            return error("window_close", "blocked by safety gate")
        result = services.executor.close_window(name or "", handle=handle, pid=pid)
        response = ok("window_close", input_payload(result.tool or "window_close", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_resize(name: str | None = None, handle: int | None = None, pid: int | None = None, width: int | None = None, height: int | None = None, x: int | None = None, y: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_resize"):
            return error("window_resize", "blocked by safety gate")
        result = services.executor.resize_window(name=name, handle=handle, pid=pid, width=width, height=height, x=x, y=y)
        response = ok("window_resize", input_payload(result.tool or "window_resize", result.ok, result.detail, result.payload), message="ok" if result.ok else "error")
        response["ok"] = result.ok
        return response

    def window_minimize(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_minimize"):
            return error("window_minimize", "blocked by safety gate")
        result = services.executor.minimize_window(name, handle=handle, pid=pid)
        response = ok("window_minimize", input_payload(result.tool or "window_minimize", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_maximize(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_maximize"):
            return error("window_maximize", "blocked by safety gate")
        result = services.executor.maximize_window(name, handle=handle, pid=pid)
        response = ok("window_maximize", input_payload(result.tool or "window_maximize", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    def window_restore(name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any]:
        if not services.safety.check("window_restore"):
            return error("window_restore", "blocked by safety gate")
        result = services.executor.restore_window(name, handle=handle, pid=pid)
        response = ok("window_restore", input_payload(result.tool or "window_restore", result.ok, result.detail, result.payload))
        response["ok"] = result.ok
        return response

    registry.register(ToolSpec(name="window_launch", kind="window", params_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}, result_schema=RESULT_SCHEMAS["input"], permission="launch_app", executor=window_launch, description="Launch an application window. Use this when the workflow starts from a named desktop app.\n\nParameters: name identifies the app or window to launch.\nReturns: standard input envelope with launch verification details. The action field is normalized to window_launch even though the executor reuses the app-launch pipeline.\nSafety: may start external applications; gated by the safety service.\nBehavior note: current payload reports the resolved target, verification source, and basic before/after window counts, but may not explicitly say whether a same-app call created a brand-new instance versus surfaced an existing one.\nExamples: {\"name\": \"calc\"}.", param_description="name: app or window to launch.", result_description="Standard input envelope with launch verification details, including requested target, matched target, detected window name, verification source, verification_status, and backend launch response.", input_examples=[{"name": "calc"}], output_examples=WINDOW_LAUNCH_OUTPUT_EXAMPLES, safety_notes="May start external applications; gated by the safety service.", implementation_notes="Wraps the launch executor and normalizes the action name to window_launch for MCP clients."))
    registry.register(ToolSpec(name="window_switch", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_switch", executor=window_switch, description="Switch to an already open window. Use this to move foreground focus between running apps or documents.\n\nParameters: provide name, handle, or pid to identify the target window. Handle wins over pid, and pid wins over name when more than one selector is present.\nReturns: standard input envelope with switch details. The payload exposes the prior active window, the current active window, their handles when available, whether the target was restored from a minimized state, and the backend match mode so clients can verify the switch happened in the intended context.\nBehavior note: use this as part of an observe -> switch -> observe loop so the current foreground target can be verified immediately after the transition. Current matching behavior is expected to normalize lightweight title variants such as leading unsaved markers, but callers should still prefer handle or pid when duplicate titles exist.\nSafety: confirm the target window before switching.\nExamples: {\"name\": \"test.txt - Notepad\"}, {\"handle\": 592712}.", param_description="name/handle/pid: target window selector. Prefer handle for duplicate titles, pid when you need process-level targeting.", result_description="Standard input envelope with switch details. Payload includes target_window, previous_window, previous_handle, current_window, current_handle, matched_by, restored_from_minimized, backend_response, backend_response_detail, backend_response_code, and verified. Top-level ok reflects post-switch verification rather than backend success alone.", input_examples=[{"name": "test.txt - Notepad"}, {"handle": 592712}], output_examples=WINDOW_SWITCH_OUTPUT_EXAMPLES, safety_notes="Confirm the target window before switching.", implementation_notes="Uses normalized title matching plus handle/pid-aware targeting. Restores minimized targets when the backend brings them to the foreground."))
    registry.register(ToolSpec(name="window_focus", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_focus", executor=window_focus, description="Bring a window into focus. Use this before typing or shortcut actions when the intended target is not currently active.\n\nParameters: provide name, handle, or pid to identify the target window.\nReturns: standard input envelope with focus details.\nSafety: use only when you need to make a specific window the foreground target.\nBehavior note: focus uses the same target-selection and verification model as window_switch. The restored_from_minimized field is intended to report whether the chosen target had to be restored before becoming foreground.\nExamples: {\"name\": \"test.txt - Notepad\"}, {\"handle\": 592712}.", param_description="name/handle/pid: target window selector. Prefer handle or pid when several windows share the same title.", result_description="Standard input envelope with focus details, including matched_by, restored_from_minimized, backend_response_detail, backend_response_code, strategy, and verified when available.", input_examples=[{"name": "test.txt - Notepad"}, {"handle": 592712}], output_examples=WINDOW_FOCUS_OUTPUT_EXAMPLES, safety_notes="Use only when you need to make a specific window the foreground target.", implementation_notes="Delegates to focus_app when available, otherwise falls back to the switch path with the same verification semantics."))
    registry.register(ToolSpec(name="window_close", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_close", executor=window_close, description="Close a window or app. High-risk; use only with explicit user intent. The final result is determined by post-close verification of the desktop state, not just the backend call result. The backend_response field records the primary close-path response, while ok reflects the verified desktop outcome.\n\nBehavior note: provide handle when duplicate titles exist. In name-only mode, the verifier may treat a drop in the number of matching windows as evidence that one instance closed, but if a matching instance remains and the verifier cannot disambiguate the target, the result can still be reported as a failure.\n\nParameters: provide name, handle, or pid to identify the window to close.\nReturns: standard input envelope with close details, close strategy, backend response, exit code, verification_mode, and post-close verification.", param_description="name/handle/pid: target window selector. Prefer handle when several windows share the same title.", result_description="Standard input envelope with close details, close strategy, backend response, exit code, before/after verification fields, and post-close verification outcome. Outcome values may include execution_failed, execution_succeeded, or degraded-success style results when the close path and observed desktop state diverge.", input_examples=[{"name": "计算器"}, {"handle": 592712}], output_examples=WINDOW_CLOSE_OUTPUT_EXAMPLES, safety_notes="High risk; gated by the safety service.", implementation_notes="Delegates to backend close_app() when available, falls back to kill_process(), and verifies by handle/pid removal or a reduced count of matching title-based windows."))
    registry.register(ToolSpec(name="window_resize", kind="window", params_schema={"type": "object", "properties": {**target_selector_schema["properties"], "width": {"type": "integer"}, "height": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": []}, result_schema=RESULT_SCHEMAS["input"], permission="window_resize", executor=window_resize, description="Resize and reposition a window. Use this for layout adjustments or multi-window workflows.\n\nParameters: identify the target window by name, handle, or pid; width and height set the size; x and y set the position.\nReturns: standard input envelope with resize details plus verification metadata about the target window and backend resize response.\nSafety: verify the target window remains usable after resizing.\nExamples: {\"name\": \"main\"}, {\"handle\": 592732, \"width\": 900, \"height\": 1200}.", param_description="name/handle/pid: target selector; width/height/x/y: desired geometry.", result_description="Standard input envelope with resize details. Payload includes before/after window snapshots, requested size and position, attempted_restore, reason, backend_response_detail, backend_response_code, and verified.", input_examples=[{"name": "main"}, {"handle": 592732, "width": 900, "height": 1200}], output_examples=[{"ok": True, "tool": "window_resize", "message": "ok", "data": {"action": "window_resize", "ok": True, "detail": "('计算器 resized to 900x1200 at 900,120.', 0)", "payload": {"before_target_window": "计算器", "before_window": {"name": "计算器", "status": "NORMAL", "handle": 592732, "window_title": "计算器"}, "before_status": "NORMAL", "before_handle": 592732, "target_window": "计算器", "after_window": {"name": "计算器", "status": "NORMAL", "handle": 592732, "window_title": "计算器"}, "after_status": "NORMAL", "after_handle": 592732, "verified": True, "reason": None, "attempted_restore": False, "requested_size": {"width": 900, "height": 1200}, "requested_position": {"x": 900, "y": 120}, "backend_response_detail": "计算器 resized to 900x1200 at 900,120.", "backend_response_code": 0}}}], safety_notes="Verify the target window remains usable after resizing.", implementation_notes="Delegates to the executor resize path and verifies the result against the resolved target handle when possible."))
    registry.register(ToolSpec(name="window_minimize", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_minimize", executor=window_minimize, description="Minimize a window. Use this to clear the foreground without closing the app.\n\nParameters: provide name, handle, or pid to identify the window to minimize.\nReturns: standard input envelope with minimize details and verification metadata.\nSafety: only use when minimizing will not interrupt active work.\nBehavior note: verification is multi-source and may consult handle visibility, active-window changes, and other post-action signals. On modern or UWP-style apps, backend success can still be returned alongside a failed verification when the observed window state does not change.\nExamples: {\"name\": \"计算器\"}, {\"handle\": 592732}.", param_description="name/handle/pid: target window selector. Prefer handle or pid to avoid ambiguity across duplicate titles.", result_description="Standard input envelope with minimize details. Payload includes before/after window snapshots, active_window_after, verification_mode, target_handle_present_after, backend_response, backend_response_detail, backend_response_code, and verified.", input_examples=[{"name": "计算器"}, {"handle": 592732}], output_examples=WINDOW_MINIMIZE_OUTPUT_EXAMPLES, safety_notes="Only use when minimizing will not interrupt active work.", implementation_notes="Delegates to the executor minimize path and verifies against the resolved target handle, pid, visibility flags, and foreground changes to reduce false negatives in duplicate-title scenarios."))
    registry.register(ToolSpec(name="window_maximize", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_maximize", executor=window_maximize, description="Maximize a window. Use this when you need more visible workspace for inspection or editing.\n\nParameters: provide name, handle, or pid to identify the window to maximize.\nReturns: standard input envelope with maximize details.\nSafety: may change layout expectations for coordinate-based actions.\nBehavior note: verification is intended to use more than the status field alone, but some applications may still report backend success while the observed snapshot remains effectively unchanged.\nExamples: {\"name\": \"计算器\"}, {\"handle\": 592712}.", param_description="name/handle/pid: target window selector. Prefer handle or pid when several matching windows exist.", result_description="Standard input envelope with maximize details. Payload includes before/after window snapshots, backend_response, backend_response_detail, backend_response_code, optional verification_mode, and verified.", input_examples=[{"name": "计算器"}, {"handle": 592712}], output_examples=WINDOW_MAXIMIZE_OUTPUT_EXAMPLES, safety_notes="May change layout expectations for coordinate-based actions.", implementation_notes="Delegates to the executor maximize path and verifies with multiple signals, including maximized status and geometry expansion when the backend status lags."))
    registry.register(ToolSpec(name="window_restore", kind="window", params_schema=target_selector_schema, result_schema=RESULT_SCHEMAS["input"], permission="window_restore", executor=window_restore, description="Restore a window to its normal state. Use this after minimizing or maximizing when you want to return to standard interaction posture.\n\nParameters: provide name, handle, or pid to identify the window to restore.\nReturns: standard input envelope with restore details and verification metadata.\nSafety: restore before the next coordinate-sensitive action if the layout changed.\nBehavior note: restore can legitimately return verified=true even when the window was already NORMAL before the call; callers that need stronger coverage should test restore from MAXIMIZED or MINIMIZED states.\nExamples: {\"name\": \"计算器\"}, {\"handle\": 592712}.", param_description="name/handle/pid: target window selector.", result_description="Standard input envelope with restore details. Payload includes before/after window snapshots, backend_response, backend_response_detail, backend_response_code, and verified.", input_examples=[{"name": "计算器"}, {"handle": 592712}], output_examples=WINDOW_RESTORE_OUTPUT_EXAMPLES, safety_notes="Restore before the next coordinate-sensitive action if the layout changed.", implementation_notes="Delegates to the executor restore path and verifies against the resolved target handle or pid when possible."))
