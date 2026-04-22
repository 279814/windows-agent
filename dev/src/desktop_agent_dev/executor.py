from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import os
import re
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

    def _launch_search_dirs(self) -> list[Path]:
        candidates = [
            Path.home() / "Desktop",
            Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
        ]
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.append(Path(onedrive) / "Desktop")
        seen: set[str] = set()
        result: list[Path] = []
        for candidate in candidates:
            candidate_key = str(candidate).lower()
            if candidate_key not in seen and candidate.is_dir():
                seen.add(candidate_key)
                result.append(candidate)
        return result

    @staticmethod
    def _canonical_launch_name(value: str) -> str:
        try:
            basename = PureWindowsPath(value).name
        except Exception:
            basename = value
        basename = basename.strip().lower()
        for suffix in (".exe", ".lnk", ".url"):
            if basename.endswith(suffix):
                basename = basename[: -len(suffix)]
                break
        basename = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", basename)
        return re.sub(r"\s+", " ", basename).strip()

    def _discover_launch_path(self, requested_target: str, alias_map: dict[str, list[str]]) -> tuple[str | None, dict[str, Any] | None]:
        normalized_requested = self._canonical_launch_name(requested_target)
        if not normalized_requested:
            return None, None

        expected_names = {normalized_requested}
        for alias in alias_map.get(normalized_requested, []):
            expected_names.add(self._canonical_launch_name(alias))
        expected_names = {item for item in expected_names if item}

        search_dirs = self._launch_search_dirs()
        if not search_dirs:
            return None, None

        discovered: list[tuple[int, str, Path]] = []
        for base_dir in search_dirs:
            try:
                for path in base_dir.rglob("*"):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in {".lnk", ".exe", ".url"}:
                        continue
                    candidate_name = self._canonical_launch_name(path.name)
                    if not candidate_name:
                        continue
                    if candidate_name in expected_names:
                        score = 0
                    elif any(candidate_name.startswith(f"{expected} ") or candidate_name.endswith(f" {expected}") for expected in expected_names):
                        score = 1
                    else:
                        continue
                    discovered.append((score, len(str(path)), path))
            except Exception:
                continue

        if not discovered:
            return None, None

        discovered.sort(key=lambda item: (item[0], item[1], item[2].name.lower()))
        best_path = discovered[0][2]
        discovery = {
            "source": "desktop_shortcut" if best_path.suffix.lower() in {".lnk", ".url"} else "desktop_executable",
            "path": str(best_path),
            "display_name": best_path.stem,
            "search_roots": [str(item) for item in search_dirs],
        }
        return str(best_path), discovery

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
            payload = {
                "text": text,
                "press_enter": press_enter,
                "clear": clear,
                "caret_position": caret_position,
                "validation": {"passed": True, "expected_change": False, "changed": None},
            }
            return self._result("input_type", f"typed:{text}{suffix}", payload=payload, tool="input_type")

        if hasattr(self._backend, "type"):
            focused_before = None
            before_value = None
            type_loc = (0, 0)
            try:
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                focused_before = getattr(state, "focused_control", None)
                if isinstance(focused_before, dict):
                    before_value = focused_before.get("value")
                    bounds = focused_before.get("bounds")
                    if bounds and len(bounds) == 4:
                        left, top, right, bottom = bounds
                        type_loc = (int((left + right) / 2), int((top + bottom) / 2))
                elif focused_before is not None:
                    before_value = getattr(focused_before, "value", None)
                    bounds = getattr(focused_before, "bounds", None)
                    if bounds and len(bounds) == 4:
                        left, top, right, bottom = bounds
                        type_loc = (int((left + right) / 2), int((top + bottom) / 2))
            except Exception:
                focused_before = None
                before_value = None
            self._backend.type(
                type_loc,
                text=text,
                press_enter=press_enter,
                clear=clear,
                caret_position=caret_position,
            )
            suffix = ":enter" if press_enter else ""
            expected_change = bool(text or clear or press_enter)
            after_value = None
            focused_after = None
            try:
                state_after = self._backend.get_state(use_vision=False, as_bytes=False)
                focused_after = getattr(state_after, "focused_control", None)
                if isinstance(focused_after, dict):
                    after_value = focused_after.get("value")
                elif focused_after is not None:
                    after_value = getattr(focused_after, "value", None)
            except Exception:
                focused_after = None
                after_value = None
            changed = before_value != after_value if before_value is not None or after_value is not None else None
            validation_passed = (not expected_change) or (changed is True)
            detail = f"typed:{text}{suffix}"
            if expected_change and validation_passed is False:
                detail = f"validation_failed:{text}{suffix}"
            payload = {
                "text": text,
                "press_enter": press_enter,
                "clear": clear,
                "caret_position": caret_position,
                "focused_before": focused_before,
                "focused_after": focused_after,
                "target_control": focused_before,
                "before_value": before_value,
                "after_value": after_value,
                "type_location": {"x": type_loc[0], "y": type_loc[1]},
                "validation": {
                    "passed": validation_passed,
                    "expected_change": expected_change,
                    "changed": changed,
                },
            }
            return self._result("input_type", detail, ok=validation_passed, payload=payload, tool="input_type")

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
            return self._result("input_launch_app", f"launch:{name}", tool="input_launch_app")

        if hasattr(self._backend, "launch_app"):
            alias_map = {
                "explorer": ["explorer.exe"],
                "file explorer": ["explorer.exe"],
                "calc": ["calc.exe"],
                "calculator": ["calc.exe"],
                "notepad": ["notepad.exe"],
                "mspaint": ["mspaint.exe"],
                "paint": ["mspaint.exe"],
            }
            requested_target = name.strip()
            normalized_key = requested_target.lower()
            matched_target = alias_map.get(normalized_key, [requested_target])[0]
            discovered_target, discovery = self._discover_launch_path(requested_target, alias_map)
            effective_target = discovered_target or matched_target
            resolved_alias = effective_target if effective_target != requested_target else None

            verification_aliases = {
                "explorer.exe": ["explorer", "file explorer", "文件资源管理器"],
                "calc.exe": ["calc", "calculator"],
                "notepad.exe": ["notepad"],
                "mspaint.exe": ["mspaint", "paint"],
            }
            verification_blacklist = {
                "calc.exe": {"mpicalc"},
            }

            def _canonical_target(value: str) -> str:
                try:
                    basename = PureWindowsPath(value).name
                except Exception:
                    basename = value
                if basename.lower().endswith(".exe"):
                    return basename[:-4].lower()
                return basename.lower()

            def _normalized_text(value: Any) -> str:
                text = str(value or "").strip().lower()
                text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", text)
                return re.sub(r"\s+", " ", text).strip()

            expected_targets = {
                _canonical_target(requested_target),
                _canonical_target(matched_target),
                _canonical_target(effective_target),
            }
            expected_phrases = {
                _normalized_text(requested_target),
                _normalized_text(matched_target),
                _normalized_text(effective_target),
            }
            for alias in verification_aliases.get(matched_target.lower(), []):
                expected_targets.add(_canonical_target(alias))
                expected_phrases.add(_normalized_text(alias))
            if discovery is not None:
                expected_phrases.add(_normalized_text(discovery.get("display_name")))

            expected_targets = {item for item in expected_targets if item}
            expected_phrases = {item for item in expected_phrases if item}
            blacklisted_targets = verification_blacklist.get(matched_target.lower(), set())

            def _contains_phrase_tokens(words: list[str], phrase_words: list[str]) -> bool:
                if not words or not phrase_words or len(phrase_words) > len(words):
                    return False
                for index in range(len(words) - len(phrase_words) + 1):
                    if words[index : index + len(phrase_words)] == phrase_words:
                        return True
                return False

            def _matches_expected(candidate: Any) -> bool:
                normalized_candidate = _normalized_text(candidate)
                if not normalized_candidate:
                    return False
                candidate_target = _canonical_target(str(candidate))
                if candidate_target in blacklisted_targets:
                    return False
                if candidate_target in expected_targets:
                    return True
                candidate_words = normalized_candidate.split()
                if set(candidate_words).intersection(expected_targets):
                    return True
                for phrase in expected_phrases:
                    phrase_words = phrase.split()
                    if phrase_words and _contains_phrase_tokens(candidate_words, phrase_words):
                        return True
                return False

            def _extract_verification_hint(value: Any) -> str | None:
                text = str(value or "")
                match = re.search(r"verification=name:([^\]\r\n]+)", text, flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                return None

            before_state = None
            after_state = None
            try:
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                before_state = getattr(state, "windows", None)
            except Exception:
                before_state = None

            response = self._backend.launch_app(effective_target)
            response_text = response[0] if isinstance(response, tuple) and response else response
            status = response[1] if isinstance(response, tuple) and len(response) > 1 and isinstance(response[1], int) else None
            pid = response[2] if isinstance(response, tuple) and len(response) > 2 and isinstance(response[2], int) else None
            launched = status == 0 if status is not None else bool(response)
            verification_hint = _extract_verification_hint(response_text)
            detected = False
            detected_name = None
            try:
                state_after = self._backend.get_state(use_vision=False, as_bytes=False)
                after_state = getattr(state_after, "windows", None)
                before_count = len(before_state) if isinstance(before_state, list) else None
                after_count = len(after_state) if isinstance(after_state, list) else None
                window_count_increased = bool(before_count is not None and after_count is not None and after_count > before_count)
                detected = window_count_increased
                active_after = getattr(state_after, "active_window", None)
                if isinstance(active_after, dict):
                    current_name = active_after.get("name") or active_after.get("window_title")
                    detected_name = current_name
                    if _matches_expected(current_name):
                        detected = True
                elif active_after is not None:
                    current_name = getattr(active_after, "name", None) or getattr(active_after, "window_title", None)
                    detected_name = current_name
                    if _matches_expected(current_name):
                        detected = True
            except Exception:
                after_state = None

            target_matches = _matches_expected(detected_name) or _matches_expected(verification_hint)
            mismatch_signals = [
                candidate
                for candidate in (detected_name, verification_hint)
                if candidate is not None and str(candidate).strip() and not _matches_expected(candidate)
            ]
            verification_evidence = bool(
                target_matches
                or detected
                or (pid is not None and pid > 0)
                or (response_text is not None and str(response_text).strip())
            )
            verification_ok = bool(launched and target_matches)
            mismatch_detected = bool(launched and not verification_ok and mismatch_signals)
            partial_ok = bool(launched and not verification_ok and not mismatch_detected and verification_evidence)
            verification_status = (
                "success"
                if verification_ok
                else ("partial" if partial_ok else ("failed" if not launched else "target_mismatch"))
            )
            result_code = (
                "OK"
                if verification_ok
                else ("PARTIAL" if partial_ok else ("LAUNCH_FAILED" if not launched else "TARGET_MISMATCH"))
            )
            detail = (
                f"launched:{name}"
                if verification_ok
                else (f"launch pending verification:{name}" if partial_ok else (f"launch failed:{name}" if not launched else f"target mismatch:{name}->{detected_name}"))
            )
            payload = {
                "name": name,
                "requested_target": requested_target,
                "matched_target": matched_target,
                "effective_target": effective_target,
                "resolved_alias": resolved_alias,
                "discovery": discovery,
                "backend_response": response,
                "status": status,
                "pid": pid,
                "before_window_count": len(before_state) if isinstance(before_state, list) else None,
                "after_window_count": len(after_state) if isinstance(after_state, list) else None,
                "window_detected": detected,
                "detected_window_name": detected_name,
                "verification_hint": verification_hint,
                "target_matches": target_matches,
                "verification_status": verification_status,
                "result_code": result_code,
                "warning": None if verification_ok else ("launch outcome could not be fully verified against the requested target" if partial_ok else "launch outcome could not be verified against the requested target"),
            }
            return self._result("input_launch_app", detail, ok=(verification_ok or partial_ok), payload=payload, tool="input_launch_app")

        raise ExecutorError("Backend does not expose launch_app().")

    def switch_window(self, name: str) -> InputResult:
        previous = self._snapshot_window(refresh=True)
        if self._backend is None:
            return self._result(
                "window_switch",
                f"switch:{name}",
                payload={
                    **self._window_payload(target_window=name, before=previous, after={"name": name, "status": None, "handle": None}),
                    "previous_window": previous.get("name") if previous else None,
                    "previous_handle": previous.get("handle") if previous else None,
                    "current_window": name,
                    "current_handle": None,
                    "matched_by": "name",
                    "restored_from_minimized": False,
                    "verified": False,
                },
                tool="window_switch",
            )

        if hasattr(self._backend, "switch_app"):
            response = self._backend.switch_app(name)
            current = self._snapshot_window(name, refresh=True)
            if current is None:
                current = self._snapshot_window(refresh=True)
            verified = bool(current and current.get("name") and str(current.get("name")).lower() == str(name).lower())
            restored_from_minimized = bool(previous and str(previous.get("status", "")).lower() == "minimized")
            payload = {
                **self._window_payload(target_window=name, before=previous, after=current),
                "name": name,
                "previous_window": previous.get("name") if previous else None,
                "previous_handle": previous.get("handle") if previous else None,
                "current_window": current.get("name") if current else None,
                "current_handle": current.get("handle") if current else None,
                "matched_by": "name",
                "restored_from_minimized": restored_from_minimized,
                "backend_response": response,
                "verified": verified,
            }
            detail = str(response[0]) if isinstance(response, tuple) and response else str(response)
            return self._result("window_switch", detail, payload=payload, tool="window_switch")

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

    def _snapshot_window(self, name: str | None = None, refresh: bool = False) -> dict[str, Any] | None:
        backend = self._backend
        if backend is None:
            return None

        def _window_to_snapshot(window: Any) -> dict[str, Any] | None:
            if window is None:
                return None
            return {
                "name": getattr(window, "name", None) or getattr(window, "window_title", None),
                "status": getattr(getattr(window, "status", None), "name", None) or getattr(window, "status", None),
                "handle": getattr(window, "handle", None),
                "window_title": getattr(window, "window_title", None) or getattr(window, "name", None),
            }

        try:
            getter = getattr(backend, "get_state", None)
            state = None
            if callable(getter):
                try:
                    state = getter(use_vision=False, as_bytes=False)
                except TypeError:
                    state = getter()
            if state is None:
                state = getattr(backend, "desktop_state", None)

            if state is not None:
                window = getattr(state, "active_window", None) if name is None else None
                if window is None and name is not None:
                    windows = list(getattr(state, "windows", []) or [])
                    for candidate in windows:
                        candidate_name = getattr(candidate, "name", None) or getattr(candidate, "window_title", None)
                        if candidate_name == name or (candidate_name and name and str(candidate_name).lower() == str(name).lower()):
                            window = candidate
                            break
                snapshot = _window_to_snapshot(window)
                if snapshot is not None:
                    return snapshot

            if refresh and name is not None:
                find_window = getattr(backend, "_find_window_by_name", None)
                if callable(find_window):
                    try:
                        target_window, _ = find_window(name, refresh_state=True)
                    except Exception:
                        target_window = None
                    snapshot = _window_to_snapshot(target_window)
                    if snapshot is not None:
                        return snapshot
        except Exception:
            return None
        return None

    def _window_payload(self, *, target_window: str | None, before: dict[str, Any] | None, after: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "before_target_window": before.get("name") if before else target_window,
            "before_window": before,
            "before_status": before.get("status") if before else None,
            "before_handle": before.get("handle") if before else None,
            "target_window": target_window,
            "after_window": after,
            "after_status": after.get("status") if after else None,
            "after_handle": after.get("handle") if after else None,
        }
        if extra:
            payload.update(extra)
        return payload

    def resize_window(
        self,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> InputResult:
        before = self._snapshot_window(name, refresh=True)
        before_status = str(before.get("status", "")).lower() if before else None
        if before is None:
            return self._result(
                "window_resize",
                f"window_not_found:{name or 'active'}",
                ok=False,
                payload={
                    "error_kind": "window_not_found",
                    "error_message": f"Window not found: {name or 'active'}",
                    **self._window_payload(target_window=name, before={"name": name, "status": None, "handle": None}, after=None),
                    "verified": False,
                    "reason": "not_found",
                    "attempted_restore": False,
                    "requested_size": {"width": width, "height": height},
                    "requested_position": {"x": x, "y": y},
                },
                tool="window_resize",
            )
        target_name = before.get("name") if before else name
        if self._backend is None:
            return self._result(
                "window_resize",
                f"resize:{name or 'active'}:{width}x{height}@{x},{y}",
                payload={**self._window_payload(target_window=target_name, before=before), "verified": False},
                tool="window_resize",
            )

        if hasattr(self._backend, "resize_app"):
            loc = (x, y) if x is not None and y is not None else None
            size = (width, height) if width is not None and height is not None else None
            reason = None
            attempted_restore = before_status in {"minimized", "maximized"}
            original_status = before_status
            if before_status == "minimized":
                restore_app = getattr(self._backend, "restore_app", None)
                if callable(restore_app):
                    attempted_restore = True
                    try:
                        restore_app(name=name)
                    except Exception:
                        after = self._snapshot_window(name, refresh=True)
                        return self._result(
                            "window_resize",
                            f"restore failed for {target_name}",
                            ok=False,
                            payload={
                                **self._window_payload(target_window=target_name, before=before, after=after),
                                "verified": False,
                                "reason": original_status,
                                "attempted_restore": attempted_restore,
                                "error_kind": "restore_failed",
                                "error_message": f"Failed to restore minimized window: {target_name}",
                                "requested_size": {"width": width, "height": height},
                                "requested_position": {"x": x, "y": y},
                            },
                            tool="window_resize",
                        )
                    before = self._snapshot_window(name, refresh=True) or before
                    before_status = str(before.get("status", "")).lower() if before else before_status
                    if before_status == "minimized":
                        after = self._snapshot_window(name, refresh=True)
                        return self._result(
                            "window_resize",
                            f"restore failed for {target_name}",
                            ok=False,
                            payload={
                                **self._window_payload(target_window=target_name, before=before, after=after),
                                "verified": False,
                                "reason": original_status,
                                "attempted_restore": attempted_restore,
                                "error_kind": "restore_failed",
                                "error_message": f"Failed to restore minimized window: {target_name}",
                                "requested_size": {"width": width, "height": height},
                                "requested_position": {"x": x, "y": y},
                            },
                            tool="window_resize",
                        )
                    reason = original_status
            elif before_status == "maximized":
                reason = original_status
                restore_app = getattr(self._backend, "restore_app", None)
                if callable(restore_app):
                    try:
                        restore_app(name=name)
                    except Exception:
                        pass
                    before = self._snapshot_window(name, refresh=True) or before
                    before_status = str(before.get("status", "")).lower() if before else before_status
                    if before_status != "maximized":
                        reason = None
            try:
                response = self._backend.resize_app(name=name, size=size, loc=loc)
            except Exception as exc:
                after = self._snapshot_window(name, refresh=True)
                return self._result(
                    "window_resize",
                    f"resize failed:{exc}",
                    ok=False,
                    payload={
                        **self._window_payload(target_window=target_name, before=before, after=after),
                        "verified": False,
                        "reason": reason,
                        "attempted_restore": attempted_restore,
                        "error_kind": "exception",
                        "error_message": str(exc),
                    },
                    tool="window_resize",
                )
            after = self._snapshot_window(name, refresh=True)
            after_status = str(after.get("status", "")).lower() if after else None
            verified = bool(after and after_status not in {"minimized", "maximized"})
            detail = str(response)
            ok_flag = verified
            if not ok_flag and reason in {"maximized", "minimized"}:
                detail = f"{target_name} is {reason}"
            if not ok_flag and after is None:
                detail = f"Resize verification failed for {target_name}."
            attempted_restore = bool(before_status in {"minimized", "maximized"})
            payload = {
                **self._window_payload(target_window=target_name, before=before, after=after),
                "verified": verified,
                "reason": reason,
                "attempted_restore": attempted_restore,
                "requested_size": {"width": width, "height": height},
                "requested_position": {"x": x, "y": y},
            }
            return self._result("window_resize", detail, ok=ok_flag, payload=payload, tool="window_resize")

        raise ExecutorError("Backend does not expose resize_app().")

    def minimize_window(self, name: str | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True) or {"name": name, "status": None, "handle": None}
        if self._backend is None:
            return self._result(
                "window_minimize",
                f"minimize:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_minimize",
            )
        if hasattr(self._backend, "minimize_app"):
            response = self._backend.minimize_app(name=name)
            after = self._snapshot_window(name, refresh=True)
            verified = bool(after and str(after.get("status", "")).lower().endswith("minimized"))
            payload = {**self._window_payload(target_window=before.get("name") if before else name, before=before, after=after), "verified": verified}
            return self._result("window_minimize", str(response), payload=payload, tool="window_minimize")
        raise ExecutorError("Backend does not expose minimize_app().")

    def maximize_window(self, name: str | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True) or {"name": name, "status": None, "handle": None}
        if self._backend is None:
            return self._result(
                "window_maximize",
                f"maximize:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_maximize",
            )
        if hasattr(self._backend, "maximize_app"):
            response = self._backend.maximize_app(name=name)
            after = self._snapshot_window(name, refresh=True)
            verified = bool(after and str(after.get("status", "")).lower() == "maximized")
            payload = {**self._window_payload(target_window=before.get("name") if before else name, before=before, after=after), "verified": verified}
            return self._result("window_maximize", str(response), payload=payload, tool="window_maximize")
        return self._result(
            "window_maximize",
            f"maximize:{name or 'active'}",
            ok=False,
            payload={
                **self._window_payload(target_window=before.get("name") if before else name, before=before),
                "verified": False,
                "error_kind": "capability_missing",
                "error_message": "Backend does not expose maximize_app().",
            },
            tool="window_maximize",
        )

    def restore_window(self, name: str | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True) or {"name": name, "status": None, "handle": None}
        if self._backend is None:
            return self._result(
                "window_restore",
                f"restore:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_restore",
            )
        if hasattr(self._backend, "restore_app"):
            response = self._backend.restore_app(name=name)
            after = self._snapshot_window(name, refresh=True)
            verified = bool(after and str(after.get("status", "")).lower() not in {"minimized", "maximized"})
            payload = {**self._window_payload(target_window=before.get("name") if before else name, before=before, after=after), "verified": verified}
            return self._result("window_restore", str(response), payload=payload, tool="window_restore")
        return self._result(
            "window_restore",
            f"restore:{name or 'active'}",
            ok=False,
            payload={
                **self._window_payload(target_window=before.get("name") if before else name, before=before),
                "verified": False,
                "error_kind": "capability_missing",
                "error_message": "Backend does not expose restore_app().",
            },
            tool="window_restore",
        )
