from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ExecutorError(RuntimeError):
    pass


@dataclass(slots=True)
class InputResult:
    action: str
    ok: bool
    detail: str
    payload: dict[str, Any] | None = None
    tool: str | None = None


class Executor:
    """Desktop execution facade with real Windows-MCP backend support."""

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    def _result(self, action: str, detail: str, ok: bool = True, payload: dict[str, Any] | None = None, tool: str | None = None) -> InputResult:
        return InputResult(action=action, ok=ok, detail=detail, payload=payload, tool=tool or action)

    def _hit_test_element(self, x: int, y: int) -> dict[str, Any]:
        backend = self._backend
        if backend is None:
            return {"type": "unknown", "name": None, "found": False, "confidence": 0.0}

        def _node_meta(node: Any) -> dict[str, Any]:
            return {
                "type": getattr(node, "control_type", "unknown") or "unknown",
                "name": getattr(node, "name", None),
                "automation_id": getattr(node, "automation_id", None),
                "class_name": getattr(node, "class_name", None),
                "role": getattr(node, "role", None),
                "process_id": getattr(node, "process_id", None),
                "window_title": getattr(node, "window_title", None),
            }

        def _bbox_area(box: Any) -> int:
            return max(1, (box.right - box.left)) * max(1, (box.bottom - box.top))

        def _is_decorative(node: Any) -> bool:
            control_type = (getattr(node, "control_type", "") or "").lower()
            role = (getattr(node, "role", "") or "").lower()
            name = (getattr(node, "name", "") or "").strip().lower()
            if control_type in {"imagecontrol", "textcontrol", "panecontrol"} and not name:
                return True
            if role in {"image", "graphic", "separator", "static text"} and not getattr(node, "automation_id", None):
                return True
            return False

        def _is_leaf(node: Any, siblings: list[Any]) -> bool:
            return all(getattr(sib, "bounding_box", None) is None or sib is node for sib in siblings)

        def _score_node(node: Any, ancestry_depth: int, sibling_index: int, sibling_count: int, is_leaf: bool) -> dict[str, Any] | None:
            box = getattr(node, "bounding_box", None)
            if box is None:
                return None
            left, top, right, bottom = box.left, box.top, box.right, box.bottom
            if not (left <= x <= right and top <= y <= bottom):
                return None

            width = max(1, right - left)
            height = max(1, bottom - top)
            area = width * height
            cx = left + width / 2
            cy = top + height / 2
            px = abs(x - cx) / width
            py = abs(y - cy) / height
            boundary_dx = min(abs(x - left), abs(x - right)) / width
            boundary_dy = min(abs(y - top), abs(y - bottom)) / height
            center_bias = max(0.0, 1.0 - min(px + py, 1.0))
            boundary_penalty = min(1.0, (boundary_dx + boundary_dy) / 2)
            leaf_bonus = 0.10 if is_leaf else 0.0
            interactive_bonus = 0.14 if (getattr(node, "name", None) or getattr(node, "automation_id", None) or getattr(node, "role", None)) else 0.0
            specificity_bonus = 0.0
            if getattr(node, "name", None):
                specificity_bonus += 0.05
            if getattr(node, "automation_id", None):
                specificity_bonus += 0.10
            if getattr(node, "class_name", None):
                specificity_bonus += 0.04
            if getattr(node, "role", None):
                specificity_bonus += 0.04
            if width <= 44 and height <= 44:
                specificity_bonus += 0.05
            if area < 18_000:
                specificity_bonus += 0.03
            decorative_penalty = 0.16 if _is_decorative(node) else 0.0
            parent_bonus = min(0.12, ancestry_depth * 0.03)
            child_rank_bonus = max(0.0, 0.06 - (sibling_index * 0.01)) if sibling_count > 1 else 0.0
            z_order_bonus = max(0.0, min(0.20, 0.20 - (sibling_index * 0.02)))
            area_penalty = min(0.12, area / 5_000_000.0)
            confidence = 0.30
            confidence += center_bias * 0.24
            confidence += leaf_bonus
            confidence += interactive_bonus
            confidence += specificity_bonus
            confidence += parent_bonus
            confidence += child_rank_bonus
            confidence += z_order_bonus
            confidence -= boundary_penalty * 0.15
            confidence -= decorative_penalty
            confidence -= area_penalty
            confidence = max(0.0, min(0.99, round(confidence, 3)))
            return {
                **_node_meta(node),
                "found": True,
                "confidence": confidence,
                "z_index": sibling_index,
                "ancestry_depth": ancestry_depth,
                "bounds": {"left": left, "top": top, "right": right, "bottom": bottom},
            }

        def _collect_nodes(state: Any) -> list[Any]:
            return list(getattr(state, "interactive_nodes", []) or [])

        def _best_from_nodes(nodes: list[Any]) -> dict[str, Any] | None:
            if not nodes:
                return None
            scored: list[tuple[float, int, dict[str, Any]]] = []
            for idx, node in enumerate(nodes):
                candidate = _score_node(node, ancestry_depth=0, sibling_index=idx, sibling_count=len(nodes), is_leaf=True)
                if candidate is None:
                    continue
                scored.append((candidate["confidence"], -idx, candidate))
            if not scored:
                return None
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return scored[0][2]

        def _best_from_hierarchy(state: Any) -> dict[str, Any] | None:
            tree_nodes = _collect_nodes(state)
            if not tree_nodes:
                return None

            scored: list[tuple[float, int, dict[str, Any]]] = []
            for idx, node in enumerate(tree_nodes):
                box = getattr(node, "bounding_box", None)
                if box is None:
                    continue
                if not (box.left <= x <= box.right and box.top <= y <= box.bottom):
                    continue
                candidate = _score_node(
                    node,
                    ancestry_depth=1 if getattr(node, "window_title", None) else 0,
                    sibling_index=idx,
                    sibling_count=len(tree_nodes),
                    is_leaf=True,
                )
                if candidate is not None:
                    scored.append((candidate["confidence"], -idx, candidate))
            if not scored:
                return None
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return scored[0][2]

        tree_state = getattr(backend, "get_tree_state", None)
        if callable(tree_state):
            try:
                state = tree_state()
            except Exception:
                state = None
            if state is not None:
                best = _best_from_hierarchy(state)
                if best is not None:
                    best["source"] = "tree_state"
                    return best

        snapshot = getattr(backend, "get_state", None)
        if callable(snapshot):
            try:
                state = snapshot(use_vision=False, as_bytes=False)
            except TypeError:
                try:
                    state = snapshot()
                except Exception:
                    state = None
            except Exception:
                state = None
            if state is not None:
                tree_state_obj = getattr(state, "tree_state", None)
                best = _best_from_nodes(_collect_nodes(tree_state_obj))
                if best is not None:
                    best["source"] = "snapshot"
                    return best

        return {"type": "unknown", "name": None, "found": False, "confidence": 0.0}

        tree_state = getattr(backend, "get_tree_state", None)
        if callable(tree_state):
            try:
                state = tree_state()
            except Exception:
                state = None
            if state is not None:
                best = _best_from_nodes(list(getattr(state, "interactive_nodes", []) or []))
                if best is not None:
                    best["source"] = "tree_state"
                    return best

        snapshot = getattr(backend, "get_state", None)
        if callable(snapshot):
            try:
                state = snapshot(use_vision=False, as_bytes=False)
            except TypeError:
                try:
                    state = snapshot()
                except Exception:
                    state = None
            except Exception:
                state = None
            if state is not None:
                tree_state_obj = getattr(state, "tree_state", None)
                best = _best_from_nodes(list(getattr(tree_state_obj, "interactive_nodes", []) or []))
                if best is not None:
                    best["source"] = "snapshot"
                    return best

        return {"type": "unknown", "name": None, "found": False, "confidence": 0.0}

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> InputResult:
        element = self._hit_test_element(x, y)
        payload = {"x": x, "y": y, "button": button, "clicks": clicks, "element": element}
        if self._backend is None:
            return self._result("input_click", f"clicked:{x},{y}:{button}:{clicks}", payload=payload, tool="input_click")

        if hasattr(self._backend, "click"):
            self._backend.click((x, y), button=button, clicks=clicks)
            return self._result("input_click", f"clicked:{x},{y}:{button}:{clicks}", payload=payload, tool="input_click")

        raise ExecutorError("Backend does not expose click().")

    def move(self, x: int, y: int) -> InputResult:
        if self._backend is None:
            return self._result("move", f"moved:{x},{y}", tool="input_move")

        if hasattr(self._backend, "move"):
            self._backend.move((x, y))
            return self._result("move", f"moved:{x},{y}", tool="input_move")

        raise ExecutorError("Backend does not expose move().")

    def drag(self, start: tuple[int, int], end: tuple[int, int]) -> InputResult:
        if self._backend is None:
            return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", tool="input_drag")

        if hasattr(self._backend, "move") and hasattr(self._backend, "drag"):
            self._backend.move(start)
            self._backend.drag(end)
            return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", tool="input_drag")

        raise ExecutorError("Backend does not expose drag support.")

    def type_text(
        self,
        text: str,
        press_enter: bool = False,
        clear: bool = False,
        caret_position: str = "idle",
    ) -> InputResult:
        if self._backend is None:
            suffix = ":enter" if press_enter else ""
            return self._result("input_type", f"typed:{text}{suffix}", tool="input_type")

        if hasattr(self._backend, "type"):
            focused_before = None
            type_loc = (0, 0)
            try:
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                focused_before = getattr(state, "focused_control", None)
                if isinstance(focused_before, dict):
                    bounds = focused_before.get("bounds")
                    if bounds and len(bounds) == 4:
                        left, top, right, bottom = bounds
                        type_loc = (int((left + right) / 2), int((top + bottom) / 2))
            except Exception:
                focused_before = None
            self._backend.type(
                type_loc,
                text=text,
                press_enter=press_enter,
                clear=clear,
                caret_position=caret_position,
            )
            suffix = ":enter" if press_enter else ""
            payload = {
                "text": text,
                "press_enter": press_enter,
                "clear": clear,
                "caret_position": caret_position,
                "focused_before": focused_before,
                "target_control": focused_before,
                "type_location": {"x": type_loc[0], "y": type_loc[1]},
            }
            return self._result("input_type", f"typed:{text}{suffix}", payload=payload, tool="input_type")

        raise ExecutorError("Backend does not expose type().")

    def multi_select(self, coordinates: list[tuple[int, int]], press_ctrl: bool = False) -> InputResult:
        if self._backend is None:
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload={"count": len(coordinates), "press_ctrl": press_ctrl},
                tool="input_multi_select",
            )

        if hasattr(self._backend, "multi_select"):
            self._backend.multi_select(press_ctrl=press_ctrl, locs=coordinates)
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload={"count": len(coordinates), "press_ctrl": press_ctrl},
                tool="input_multi_select",
            )

        raise ExecutorError("Backend does not expose multi_select().")

    def multi_edit(self, edits: list[tuple[int, int, str]]) -> InputResult:
        if self._backend is None:
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload={"count": len(edits)}, tool="input_multi_edit")

        if hasattr(self._backend, "multi_edit"):
            self._backend.multi_edit(edits)
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload={"count": len(edits)}, tool="input_multi_edit")

        raise ExecutorError("Backend does not expose multi_edit().")

    def shortcut(self, keys: str) -> InputResult:
        if self._backend is None:
            return self._result(
                "shortcut",
                f"shortcut:{keys}",
                payload={
                    "keys": keys,
                    "target_window": None,
                    "focus_before": None,
                    "focus_after": None,
                    "focus_changed": None,
                    "injection_result": {"status": "sent", "method": "synthetic"},
                },
                tool="input_shortcut",
            )

        if hasattr(self._backend, "shortcut"):
            focus_before = None
            target_window = None
            try:
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                focused = getattr(state, "focused_control", None)
                if isinstance(focused, dict):
                    focus_before = focused.get("window_title") or focused.get("name") or focused.get("automation_id")
                    target_window = focus_before
                elif focused is not None:
                    focus_before = getattr(focused, "window_title", None) or getattr(focused, "name", None)
                    target_window = focus_before
            except Exception:
                focus_before = None
                target_window = None

            self._backend.shortcut(keys)

            focus_after = None
            try:
                state_after = self._backend.get_state(use_vision=False, as_bytes=False)
                focused_after = getattr(state_after, "focused_control", None)
                if isinstance(focused_after, dict):
                    focus_after = focused_after.get("window_title") or focused_after.get("name") or focused_after.get("automation_id")
                elif focused_after is not None:
                    focus_after = getattr(focused_after, "window_title", None) or getattr(focused_after, "name", None)
            except Exception:
                focus_after = None

            payload = {
                "keys": keys,
                "target_window": target_window,
                "focus_before": focus_before,
                "focus_after": focus_after,
                "focus_changed": (focus_before != focus_after) if (focus_before is not None or focus_after is not None) else None,
                "injection_result": {"status": "sent", "method": "backend.shortcut"},
            }
            return self._result("input_shortcut", f"shortcut:{keys}", payload=payload, tool="input_shortcut")

        raise ExecutorError("Backend does not expose shortcut().")

    def scroll(self, direction: str, amount: int = 1) -> InputResult:
        if self._backend is None:
            return self._result("scroll", f"scrolled:{direction}:{amount}", tool="input_scroll")

        if hasattr(self._backend, "scroll"):
            self._backend.scroll(direction=direction, wheel_times=amount)
            return self._result("scroll", f"scrolled:{direction}:{amount}", tool="input_scroll")

        raise ExecutorError("Backend does not expose scroll().")

    def launch_app(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_launch", f"launch:{name}", tool="window_launch")

        if hasattr(self._backend, "launch_app"):
            response = self._backend.launch_app(name)
            return self._result("window_launch", str(response), tool="window_launch")

        raise ExecutorError("Backend does not expose launch_app().")

    def switch_window(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result(
                "window_switch",
                f"switch:{name}",
                payload={
                    "name": name,
                    "target_window": name,
                    "previous_window": None,
                    "previous_handle": None,
                    "current_window": name,
                    "current_handle": None,
                    "matched_by": "name",
                },
                tool="window_switch",
            )

        if hasattr(self._backend, "switch_app"):
            previous_window = None
            previous_handle = None
            restored_from_minimized = None
            try:
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                active = getattr(state, "active_window", None)
                if isinstance(active, dict):
                    previous_window = active.get("name") or active.get("window_title")
                    previous_handle = active.get("handle")
                    status = str(active.get("status") or "").lower()
                    restored_from_minimized = status == "minimized"
                elif active is not None:
                    previous_window = getattr(active, "name", None) or getattr(active, "window_title", None)
                    previous_handle = getattr(active, "handle", None)
                    status = str(getattr(active, "status", "") or "").lower()
                    restored_from_minimized = status == "minimized"
            except Exception:
                previous_window = None
                previous_handle = None
                restored_from_minimized = None

            response = self._backend.switch_app(name)
            current_window = None
            current_handle = None
            matched_by = "name"
            try:
                state_after = self._backend.get_state(use_vision=False, as_bytes=False)
                active_after = getattr(state_after, "active_window", None)
                if isinstance(active_after, dict):
                    current_window = active_after.get("name") or active_after.get("window_title")
                    current_handle = active_after.get("handle")
                    matched_by = active_after.get("matched_by") or matched_by
                elif active_after is not None:
                    current_window = getattr(active_after, "name", None) or getattr(active_after, "window_title", None)
                    current_handle = getattr(active_after, "handle", None)
                    matched_by = getattr(active_after, "matched_by", None) or matched_by
            except Exception:
                current_window = None
                current_handle = None

            payload = {
                "name": name,
                "target_window": name,
                "previous_window": previous_window,
                "previous_handle": previous_handle,
                "current_window": current_window,
                "current_handle": current_handle,
                "matched_by": matched_by,
                "restored_from_minimized": restored_from_minimized,
                "backend_response": response,
            }
            detail = str(response[0]) if isinstance(response, tuple) and response else str(response)
            return self._result("window_switch", detail, payload={**payload, "backend_response": response}, tool="window_switch")

        raise ExecutorError("Backend does not expose switch_app().")

    def focus_window(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_focus", f"focus:{name}", tool="window_focus")

        if hasattr(self._backend, "focus_app"):
            response = self._backend.focus_app(name)
            return self._result("window_focus", str(response), tool="window_focus")

        return self.switch_window(name)

    def close_window(self, name: str) -> InputResult:
        def _normalize_backend_response(response: Any) -> tuple[str, int | None]:
            if isinstance(response, tuple) and len(response) >= 2:
                return str(response[0]), response[1] if isinstance(response[1], int) else None
            return str(response), 0

        def _window_record(window: Any) -> dict[str, Any] | None:
            if window is None:
                return None
            if isinstance(window, dict):
                return {
                    "name": window.get("name") or window.get("window_title"),
                    "handle": window.get("handle"),
                    "status": window.get("status"),
                    "window_title": window.get("window_title") or window.get("name"),
                }
            return {
                "name": getattr(window, "name", None) or getattr(window, "window_title", None),
                "handle": getattr(window, "handle", None),
                "status": getattr(window, "status", None),
                "window_title": getattr(window, "window_title", None) or getattr(window, "name", None),
            }

        def _window_signature(state: Any) -> dict[str, Any] | None:
            if state is None:
                return None
            active = getattr(state, "active_window", None)
            windows = getattr(state, "windows", None)
            if windows is None and isinstance(state, dict):
                active = state.get("active_window")
                windows = state.get("windows")
            window_list = []
            if isinstance(windows, list):
                for window in windows:
                    record = _window_record(window)
                    if record is not None:
                        window_list.append(record)
            return {"active_window": _window_record(active), "windows": window_list}

        def _capture_state() -> dict[str, Any] | None:
            getter = getattr(self._backend, "get_state", None)
            if not callable(getter):
                return None
            try:
                state = getter(use_vision=False, as_bytes=False)
            except TypeError:
                try:
                    state = getter()
                except Exception:
                    return None
            except Exception:
                return None
            return _window_signature(state)

        def _close_outcome(before: dict[str, Any] | None, after: dict[str, Any] | None, detail: str, exit_code: int | None, strategy: str, backend_response: Any, requested_close_path: str) -> InputResult:
            before_active = before.get("active_window") if before else None
            after_active = after.get("active_window") if after else None
            before_name = before_active.get("name") if before_active else None
            target_label = name

            def _find_window(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
                if snapshot is None:
                    return None
                for window in snapshot.get("windows", []):
                    if not isinstance(window, dict):
                        continue
                    candidate_name = window.get("name") or window.get("window_title")
                    candidate_title = window.get("window_title") or candidate_name
                    if candidate_name == target_label or candidate_title == target_label:
                        return window
                active_window = snapshot.get("active_window")
                if isinstance(active_window, dict):
                    candidate_name = active_window.get("name") or active_window.get("window_title")
                    candidate_title = active_window.get("window_title") or candidate_name
                    if candidate_name == target_label or candidate_title == target_label:
                        return active_window
                return None

            before_target = _find_window(before)
            after_target = _find_window(after)
            before_handle = before_target.get("handle") if before_target else None
            after_handle = after_target.get("handle") if after_target else None
            before_present = before_target is not None
            after_present = after_target is not None
            gone = before_present and not after_present
            changed = before_handle is not None and after_handle is not None and after_handle != before_handle
            verified = gone or changed
            normalized_detail = detail
            normalized_exit_code = exit_code
            normalized_backend_response = backend_response
            outcome = "execution_failed"
            ok = False

            if verified:
                ok = True
                if strategy == "backend.close_app" and (exit_code not in (None, 0) or detail.lower().startswith(("failed", "error"))):
                    outcome = "success_wm_close_degraded"
                elif strategy == "backend.kill_process":
                    outcome = "success_wm_close_degraded"
                else:
                    outcome = "execution_succeeded"
                normalized_detail = f"Closed {target_label}."
                normalized_exit_code = 0
                normalized_backend_response = (normalized_detail, 0)
            elif before_present:
                outcome = "execution_failed"
                normalized_exit_code = normalized_exit_code if normalized_exit_code not in (None, 0) else 1
                if detail.lower().startswith(("failed", "error")):
                    normalized_detail = detail
                else:
                    normalized_detail = f"Close verification failed for {target_label}."

            return self._result(
                "window_close",
                normalized_detail,
                ok=ok,
                payload={
                    "name": name,
                    "target_window": target_label,
                    "close_strategy": strategy,
                    "requested_close_path": requested_close_path,
                    "backend_response": normalized_backend_response,
                    "exit_code": normalized_exit_code,
                    "before_window": before,
                    "after_window": after,
                    "post_close_verified": verified,
                    "outcome": outcome if ok or before_present else "capability_missing",
                },
                tool="window_close",
            )

        if self._backend is None:
            return self._result(
                "window_close",
                f"close:{name}",
                ok=False,
                payload={
                    "name": name,
                    "target_window": name,
                    "close_strategy": "capability_missing",
                    "requested_close_path": "capability_missing",
                    "backend_response": None,
                    "exit_code": None,
                    "before_window": None,
                    "after_window": None,
                    "post_close_verified": False,
                    "outcome": "capability_missing",
                },
                tool="window_close",
            )

        before = _capture_state()
        close_app = getattr(self._backend, "close_app", None)
        if callable(close_app):
            response = close_app(name)
            detail, exit_code = _normalize_backend_response(response)
            after = _capture_state()
            return _close_outcome(before, after, detail, exit_code, "backend.close_app", response, "wm_close")

        kill_process = getattr(self._backend, "kill_process", None)
        if callable(kill_process):
            response = kill_process(name=name, force=False)
            detail, exit_code = _normalize_backend_response(response)
            after = _capture_state()
            result = _close_outcome(before, after, detail, exit_code, "backend.kill_process", response, "kill_process")
            if result.payload is not None:
                result.payload["outcome"] = "success_wm_close_degraded" if result.ok else result.payload.get("outcome", "execution_failed")
            return result

        return self._result(
            "window_close",
            f"close:{name}",
            ok=False,
            payload={
                "name": name,
                "target_window": name,
                "close_strategy": "capability_missing",
                "requested_close_path": "capability_missing",
                "backend_response": None,
                "exit_code": None,
                "before_window": before,
                "after_window": None,
                "post_close_verified": False,
                "outcome": "capability_missing",
            },
            tool="window_close",
        )

    def resize_window(
        self,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> InputResult:
        if self._backend is None:
            return self._result(
                "window_resize",
                f"resize:{name or 'active'}:{width}x{height}@{x},{y}",
                payload={"name": name, "width": width, "height": height, "x": x, "y": y},
                tool="window_resize",
            )

        if hasattr(self._backend, "resize_app"):
            loc = (x, y) if x is not None and y is not None else None
            size = (width, height) if width is not None and height is not None else None
            response = self._backend.resize_app(name=name, size=size, loc=loc)
            return self._result(
                "window_resize",
                str(response),
                payload={"name": name, "width": width, "height": height, "x": x, "y": y},
                tool="window_resize",
            )

        raise ExecutorError("Backend does not expose resize_app().")

    def minimize_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_minimize", f"minimize:{name or 'active'}", tool="window_minimize")
        if hasattr(self._backend, "minimize_app"):
            response = self._backend.minimize_app(name=name)
            return self._result("window_minimize", str(response), tool="window_minimize")
        raise ExecutorError("Backend does not expose minimize_app().")

    def maximize_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_maximize", f"maximize:{name or 'active'}", tool="window_maximize")
        if hasattr(self._backend, "maximize_app"):
            response = self._backend.maximize_app(name=name)
            return self._result("window_maximize", str(response), tool="window_maximize")
        raise ExecutorError("Backend does not expose maximize_app().")

    def restore_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_restore", f"restore:{name or 'active'}", tool="window_restore")
        if hasattr(self._backend, "restore_app"):
            response = self._backend.restore_app(name=name)
            return self._result("window_restore", str(response), tool="window_restore")
        raise ExecutorError("Backend does not expose restore_app().")
