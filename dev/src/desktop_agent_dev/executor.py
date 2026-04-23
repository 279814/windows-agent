from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import os
import re
import subprocess
import time
from typing import Any

from datetime import datetime, timezone

from .motion import MotionAction, MotionScheduler, MotionResult, MotionPhase, MotionExecutionError
from .overlay import OverlayRenderer
from .state import TaskStore


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

    def __init__(self, backend: Any | None = None, motion_scheduler: MotionScheduler | None = None, overlay_renderer: OverlayRenderer | None = None, task_store: TaskStore | None = None) -> None:
        self._backend = backend
        self._window_history: list[dict[str, Any]] = []
        self._motion_scheduler = motion_scheduler or MotionScheduler()
        self._overlay_renderer = overlay_renderer or OverlayRenderer()
        self._task_store = task_store or TaskStore()

    def _result(self, action: str, detail: str, ok: bool = True, payload: dict[str, Any] | None = None, tool: str | None = None) -> InputResult:
        return InputResult(action=action, ok=ok, detail=detail, payload=payload, tool=tool or action)

    def _overlay_snapshot_payload(self) -> dict[str, Any]:
        overlay_snapshot = self._overlay_renderer.snapshot()
        return {
            "visible": overlay_snapshot.visible,
            "cursor_x": overlay_snapshot.cursor_x,
            "cursor_y": overlay_snapshot.cursor_y,
            "trail": [list(point) for point in overlay_snapshot.trail],
            "click_ripples": [dict(ripple) for ripple in overlay_snapshot.click_ripples],
            "drag_active": overlay_snapshot.drag_active,
            "drag_start": overlay_snapshot.drag_start,
            "display_id": overlay_snapshot.display_id,
            "scale_factor": overlay_snapshot.scale_factor,
            "monitor_bounds": [dict(bounds) for bounds in overlay_snapshot.monitor_bounds],
            "metadata": dict(overlay_snapshot.metadata),
            "last_action_kind": overlay_snapshot.last_action_kind,
            "last_action_status": overlay_snapshot.last_action_status,
            "last_target": overlay_snapshot.last_target,
            "last_error": overlay_snapshot.last_error,
            "last_verified_at": overlay_snapshot.last_verified_at,
            "timeline": [dict(item) for item in overlay_snapshot.timeline],
        }

    def _sync_overlay_from_context(self, *, active_window: dict[str, Any] | None = None, phase: str | None = None, kind: str | None = None, target: tuple[int, int] | None = None, drag_start: tuple[int, int] | None = None, drag_active: bool | None = None) -> None:
        try:
            display_id = None
            scale_factor = 1.0
            monitor_bounds: list[dict[str, int]] = []
            if hasattr(self._backend, "get_state"):
                state = self._backend.get_state(use_vision=False, as_bytes=False)
                display_id = getattr(state, "display_id", None) or getattr(state, "monitor_id", None)
                scale_factor = float(getattr(state, "dpi_scale", 1.0) or 1.0)
                bounds = getattr(state, "monitor_bounds", None)
                if isinstance(bounds, list):
                    monitor_bounds = [dict(item) for item in bounds if isinstance(item, dict)]
            self._overlay_renderer.set_display_context(display_id=display_id, scale_factor=scale_factor, monitor_bounds=monitor_bounds)
            if active_window and active_window.get("handle") is not None:
                self._overlay_renderer.show()
            if target is not None:
                self._overlay_renderer.update_cursor(target[0], target[1])
            if drag_active is not None:
                start = None if drag_start is None else {"x": drag_start[0], "y": drag_start[1]}
                self._overlay_renderer.set_drag_state(drag_active, start=start)
            if active_window is not None:
                self._overlay_renderer.attach_motion(
                    phase or "ready",
                    {
                        "kind": kind,
                        "active_window": active_window,
                        "last_target": None if target is None else {"x": target[0], "y": target[1]},
                    },
                )
        except Exception:
            pass

    def _ensure_window_ready(self, name: str | None = None, handle: int | None = None, pid: int | None = None) -> dict[str, Any] | None:
        active = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
        if active is None and self._backend is not None and hasattr(self._backend, "focus_app"):
            target_label = name or ""
            if handle is not None:
                self._native_focus_window(handle)
            else:
                try:
                    self._backend.focus_app(target_label)
                except Exception:
                    pass
            active = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
        if active is not None:
            self._sync_overlay_from_context(active_window=active, phase="focused", kind="window_focus", target=None)
        return active

    def _run_input_with_recovery(self, *, operation: str, recover_name: str | None = None, recover_handle: int | None = None, recover_pid: int | None = None, runner):
        attempt_notes: list[dict[str, Any]] = []
        before = self._ensure_window_ready(recover_name, recover_handle, recover_pid)
        if before is not None:
            attempt_notes.append({"step": "ensure_window_ready", "window": before.get("name"), "handle": before.get("handle")})
        self._overlay_renderer.record_timeline("input_begin", {"at": datetime.now(timezone.utc).isoformat(), "kind": operation, "phase": "begin", "operation": operation, "recover_name": recover_name, "recover_handle": recover_handle, "recover_pid": recover_pid})
        try:
            result = runner()
        except Exception as exc:
            attempt_notes.append({"step": "runner_error", "error": str(exc)})
            self._overlay_renderer.record_timeline("input_error", {"at": datetime.now(timezone.utc).isoformat(), "kind": operation, "phase": "error", "operation": operation, "error": str(exc)})
            before_retry = self._ensure_window_ready(recover_name, recover_handle, recover_pid)
            attempt_notes.append({"step": "recover_window", "window": None if before_retry is None else before_retry.get("name"), "handle": None if before_retry is None else before_retry.get("handle")})
            self._overlay_renderer.record_timeline("input_retry", {"at": datetime.now(timezone.utc).isoformat(), "kind": operation, "phase": "retry", "operation": operation, "window": None if before_retry is None else before_retry.get("name")})
            result = runner()
        self._overlay_renderer.record_timeline("input_end", {"at": datetime.now(timezone.utc).isoformat(), "kind": operation, "phase": "end", "operation": operation, "ok": result.ok, "detail": result.detail})
        if result.payload is None:
            result.payload = {}
        result.payload["recovery_attempts"] = attempt_notes
        result.payload["overlay_state"] = self._overlay_snapshot_payload()
        result.payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
        return result

    def _task_motion_event(self, *, kind: str, phase: MotionPhase, action: MotionAction | None = None, error_message: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": kind,
            "phase": phase.value,
            "last_error": error_message,
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
        }
        if action is not None:
            payload["last_target"] = {"x": action.end.x, "y": action.end.y}
            payload["duration_ms"] = action.duration_ms
            payload["steps"] = action.metadata.get("steps")
        return payload

    def _update_task_state(self, task_id: str | None, *, action: dict[str, Any] | None = None, verified: bool = False, error_message: str | None = None) -> None:
        if not task_id:
            return
        try:
            self._task_store.advance(task_id, action=action, verified=verified, error_message=error_message)
        except Exception:
            pass

    def motion_preview(
        self,
        kind: str,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int | None = None,
        steps: int = 16,
        hover_ms: int = 0,
        jitter_px: int = 0,
        accel: float = 1.0,
        decel: float = 1.0,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        action = self._motion_scheduler.plan(kind=kind, start=start, end=end, duration_ms=duration_ms, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel)
        result = self._motion_scheduler.plan_result(action, steps=steps)
        self._overlay_renderer.update_cursor(end[0], end[1])
        self._overlay_renderer.attach_motion(result.phase.value, {"kind": kind, "steps": len(result.path), "hover_ms": hover_ms, "jitter_px": jitter_px, "accel": accel, "decel": decel, "last_target": {"x": end[0], "y": end[1]}})
        self._update_task_state(task_id, action=self._task_motion_event(kind=kind, phase=result.phase, action=action), verified=False)
        overlay_snapshot = self._overlay_renderer.snapshot()
        return {
            "ok": result.ok,
            "phase": result.phase.value,
            "action": {
                "kind": result.action.kind,
                "start": {"x": result.action.start.x, "y": result.action.start.y},
                "end": {"x": result.action.end.x, "y": result.action.end.y},
                "duration_ms": result.action.duration_ms,
                "easing": result.action.easing,
                "metadata": result.action.metadata,
            },
            "path": [{"x": point.x, "y": point.y, "t": point.t} for point in result.path],
            "detail": result.detail,
            "metadata": result.metadata,
            "overlay_state": {
                "visible": overlay_snapshot.visible,
                "cursor_x": overlay_snapshot.cursor_x,
                "cursor_y": overlay_snapshot.cursor_y,
                "trail": [list(point) for point in overlay_snapshot.trail],
                "metadata": overlay_snapshot.metadata,
                "last_action_kind": overlay_snapshot.last_action_kind,
                "last_action_status": overlay_snapshot.last_action_status,
                "last_target": overlay_snapshot.last_target,
                "last_error": overlay_snapshot.last_error,
                "last_verified_at": overlay_snapshot.last_verified_at,
            },
            "task_state": self._task_store.get(task_id).status if task_id else None,
        }

    def motion_execute(
        self,
        kind: str,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int | None = None,
        steps: int = 16,
        hover_ms: int = 0,
        jitter_px: int = 0,
        accel: float = 1.0,
        decel: float = 1.0,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        action = self._motion_scheduler.plan(kind=kind, start=start, end=end, duration_ms=duration_ms, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel)
        try:
            result = self._motion_scheduler.execute(action, steps=steps)
        except MotionExecutionError as exc:
            self._overlay_renderer.attach_motion(MotionPhase.FAILED.value, {"kind": kind, "last_error": str(exc), "last_target": {"x": end[0], "y": end[1]}})
            self._update_task_state(task_id, action=self._task_motion_event(kind=kind, phase=MotionPhase.FAILED, action=action, error_message=str(exc)), error_message=str(exc))
            overlay_snapshot = self._overlay_renderer.snapshot()
            return {
                "ok": False,
                "phase": MotionPhase.FAILED.value,
                "action": {"kind": kind, "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}, "duration_ms": action.duration_ms, "easing": action.easing, "metadata": action.metadata},
                "path": [],
                "detail": str(exc),
                "metadata": {"error": "execution_failed"},
                "overlay_state": {"visible": overlay_snapshot.visible, "cursor_x": overlay_snapshot.cursor_x, "cursor_y": overlay_snapshot.cursor_y, "trail": [list(point) for point in overlay_snapshot.trail], "metadata": overlay_snapshot.metadata, "last_action_kind": overlay_snapshot.last_action_kind, "last_action_status": overlay_snapshot.last_action_status, "last_target": overlay_snapshot.last_target, "last_error": overlay_snapshot.last_error, "last_verified_at": overlay_snapshot.last_verified_at},
                "task_state": self._task_store.get(task_id).status if task_id else None,
            }
        except Exception as exc:
            self._overlay_renderer.attach_motion(MotionPhase.FAILED.value, {"kind": kind, "last_error": str(exc), "last_target": {"x": end[0], "y": end[1]}})
            self._update_task_state(task_id, action=self._task_motion_event(kind=kind, phase=MotionPhase.FAILED, action=action, error_message=str(exc)), error_message=str(exc))
            overlay_snapshot = self._overlay_renderer.snapshot()
            return {
                "ok": False,
                "phase": MotionPhase.FAILED.value,
                "action": {"kind": kind, "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}, "duration_ms": action.duration_ms, "easing": action.easing, "metadata": action.metadata},
                "path": [],
                "detail": str(exc),
                "metadata": {"error": "execution_failed"},
                "overlay_state": {"visible": overlay_snapshot.visible, "cursor_x": overlay_snapshot.cursor_x, "cursor_y": overlay_snapshot.cursor_y, "trail": [list(point) for point in overlay_snapshot.trail], "metadata": overlay_snapshot.metadata, "last_action_kind": overlay_snapshot.last_action_kind, "last_action_status": overlay_snapshot.last_action_status, "last_target": overlay_snapshot.last_target, "last_error": overlay_snapshot.last_error, "last_verified_at": overlay_snapshot.last_verified_at},
                "task_state": self._task_store.get(task_id).status if task_id else None,
            }
        self._overlay_renderer.update_cursor(end[0], end[1])
        self._overlay_renderer.attach_motion(result.phase.value, {"kind": kind, "steps": len(result.path), "hover_ms": hover_ms, "jitter_px": jitter_px, "accel": accel, "decel": decel, "last_target": {"x": end[0], "y": end[1]}})
        self._update_task_state(task_id, action=self._task_motion_event(kind=kind, phase=result.phase, action=action), verified=True)
        overlay_snapshot = self._overlay_renderer.snapshot()
        return {"ok": result.ok, "phase": result.phase.value, "action": {"kind": result.action.kind, "start": {"x": result.action.start.x, "y": result.action.start.y}, "end": {"x": result.action.end.x, "y": result.action.end.y}, "duration_ms": result.action.duration_ms, "easing": result.action.easing, "metadata": result.action.metadata}, "path": [{"x": point.x, "y": point.y, "t": point.t} for point in result.path], "detail": result.detail, "metadata": result.metadata, "overlay_state": {"visible": overlay_snapshot.visible, "cursor_x": overlay_snapshot.cursor_x, "cursor_y": overlay_snapshot.cursor_y, "trail": [list(point) for point in overlay_snapshot.trail], "metadata": overlay_snapshot.metadata, "last_action_kind": overlay_snapshot.last_action_kind, "last_action_status": overlay_snapshot.last_action_status, "last_target": overlay_snapshot.last_target, "last_error": overlay_snapshot.last_error, "last_verified_at": overlay_snapshot.last_verified_at}, "task_state": self._task_store.get(task_id).status if task_id else None}

    _SHORTCUT_NOISE_PATTERNS = (
        r"\s*-\s*快捷方式$",
        r"\s*快捷方式$",
        r"\s*-\s*shortcut$",
        r"\s*shortcut$",
    )
    _VERSION_TAIL_PATTERNS = (
        r"\s+v?\d{4}(?:\.\d+){0,3}$",
        r"\s+v?\d+(?:\.\d+){1,3}$",
        r"\s+(?:version|ver)\.?\s*\d+(?:\.\d+){0,3}$",
    )

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
    def _strip_launch_noise(value: str) -> str:
        try:
            basename = PureWindowsPath(value).name
        except Exception:
            basename = value
        basename = basename.strip()
        previous = None
        while basename and basename != previous:
            previous = basename
            for pattern in Executor._SHORTCUT_NOISE_PATTERNS:
                basename = re.sub(pattern, "", basename, flags=re.IGNORECASE)
            for suffix in (".lnk", ".url", ".exe"):
                if basename.lower().endswith(suffix):
                    basename = basename[: -len(suffix)].rstrip()
        basename = re.sub(r"\s+", " ", basename)
        return basename.strip()

    @classmethod
    def _canonical_launch_name(cls, value: str) -> str:
        basename = cls._strip_launch_noise(value).lower()
        basename = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", basename)
        return re.sub(r"\s+", " ", basename).strip()

    @classmethod
    def _launch_name_variants(cls, value: str) -> list[str]:
        raw = cls._strip_launch_noise(value)
        variants: list[str] = []
        seen: set[str] = set()

        def _add(candidate: str) -> None:
            normalized = cls._canonical_launch_name(candidate)
            if normalized and normalized not in seen:
                seen.add(normalized)
                variants.append(normalized)

        _add(value)
        _add(raw)
        for pattern in cls._VERSION_TAIL_PATTERNS:
            shortened = re.sub(pattern, "", raw, flags=re.IGNORECASE).strip()
            if shortened and shortened != raw:
                _add(shortened)
        return variants

    @staticmethod
    def _resolve_shortcut_target(path: Path) -> str | None:
        if path.suffix.lower() != ".lnk":
            return str(path)
        try:
            escaped_path = str(path).replace("'", "''")
            script = (
                "$shell = New-Object -ComObject WScript.Shell; "
                f"$shortcut = $shell.CreateShortcut('{escaped_path}'); "
                "if ($shortcut.TargetPath) { Write-Output $shortcut.TargetPath }"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except Exception:
            return None
        target = (completed.stdout or "").strip()
        if not target:
            return None
        return target if Path(target).exists() else None

    def _discover_launch_path(self, requested_target: str, alias_map: dict[str, list[str]]) -> tuple[str | None, dict[str, Any] | None]:
        expected_names: set[str] = set(self._launch_name_variants(requested_target))
        for variant in list(expected_names):
            for alias in alias_map.get(variant, []):
                expected_names.update(self._launch_name_variants(alias))
        if not expected_names:
            return None, None

        search_dirs = self._launch_search_dirs()
        if not search_dirs:
            return None, None

        discovered: list[tuple[int, int, str, Path, str | None]] = []
        for base_dir in search_dirs:
            try:
                for path in base_dir.rglob("*"):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in {".lnk", ".exe", ".url"}:
                        continue
                    candidate_variants = set(self._launch_name_variants(path.name))
                    shortcut_target = self._resolve_shortcut_target(path) if path.suffix.lower() == ".lnk" else str(path)
                    if shortcut_target:
                        candidate_variants.update(self._launch_name_variants(shortcut_target))
                    if not candidate_variants:
                        continue
                    if candidate_variants.intersection(expected_names):
                        score = 0
                    elif any(
                        candidate.startswith(f"{expected} ") or candidate.endswith(f" {expected}")
                        for candidate in candidate_variants
                        for expected in expected_names
                    ):
                        score = 1
                    else:
                        continue
                    resolved_target = shortcut_target if shortcut_target and Path(shortcut_target).exists() else None
                    target_bonus = 0 if resolved_target else 1
                    discovered.append((score, target_bonus, len(str(path)), path, resolved_target))
            except Exception:
                continue

        if not discovered:
            return None, None

        discovered.sort(key=lambda item: (item[0], item[1], item[2], item[3].name.lower()))
        best_path = discovered[0][3]
        resolved_target = discovered[0][4]
        discovery = {
            "source": "desktop_shortcut" if best_path.suffix.lower() in {".lnk", ".url"} else "desktop_executable",
            "path": str(best_path),
            "display_name": best_path.stem,
            "resolved_target_path": resolved_target,
            "target_path_verified": bool(resolved_target),
            "search_roots": [str(item) for item in search_dirs],
        }
        return (resolved_target or str(best_path)), discovery

    def _snapshot_launch_state(self) -> tuple[Any | None, list[Any] | None]:
        try:
            state = self._backend.get_state(use_vision=False, as_bytes=False)
        except Exception:
            return None, None
        return getattr(state, "active_window", None), getattr(state, "windows", None)

    def _safe_backend_state(self) -> Any | None:
        backend = self._backend
        if backend is None:
            return None
        getter = getattr(backend, "get_state", None)
        if not callable(getter):
            return None
        try:
            return getter(use_vision=False, as_bytes=False)
        except TypeError:
            try:
                return getter()
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _coerce_bounds(bounds: Any) -> dict[str, int] | None:
        if bounds is None:
            return None
        if isinstance(bounds, dict):
            left = bounds.get("left")
            top = bounds.get("top")
            right = bounds.get("right")
            bottom = bounds.get("bottom")
        elif isinstance(bounds, (list, tuple)) and len(bounds) == 4:
            left, top, right, bottom = bounds
        else:
            left = getattr(bounds, "left", None)
            top = getattr(bounds, "top", None)
            right = getattr(bounds, "right", None)
            bottom = getattr(bounds, "bottom", None)
        if None in {left, top, right, bottom}:
            return None
        try:
            return {
                "left": int(left),
                "top": int(top),
                "right": int(right),
                "bottom": int(bottom),
            }
        except Exception:
            return None

    @classmethod
    def _point_within_bounds(cls, x: int, y: int, bounds: Any) -> bool:
        coerced = cls._coerce_bounds(bounds)
        if coerced is None:
            return False
        return coerced["left"] <= x <= coerced["right"] and coerced["top"] <= y <= coerced["bottom"]

    def _window_history_key(self, snapshot: dict[str, Any] | None) -> tuple[Any, Any, Any] | None:
        if snapshot is None:
            return None
        return (
            snapshot.get("handle"),
            snapshot.get("pid"),
            self._normalize_window_name(snapshot.get("name") or snapshot.get("window_title")),
        )

    def _remember_window_snapshots(self, windows: list[dict[str, Any]]) -> None:
        for snapshot in windows:
            key = self._window_history_key(snapshot)
            if key is None:
                continue
            self._window_history = [item for item in self._window_history if self._window_history_key(item) != key]
            self._window_history.insert(0, dict(snapshot))
        if len(self._window_history) > 64:
            self._window_history = self._window_history[:64]

    def _snapshot_windows_from_history(self) -> list[dict[str, Any]]:
        return [dict(snapshot) for snapshot in self._window_history]

    def _serialize_control(self, control: Any) -> dict[str, Any] | None:
        if control is None:
            return None
        if isinstance(control, dict):
            bounds = self._coerce_bounds(control.get("bounds") or control.get("bounding_box"))
            return {
                "name": control.get("name"),
                "value": control.get("value"),
                "text": control.get("text"),
                "control_type": control.get("control_type") or control.get("type"),
                "automation_id": control.get("automation_id"),
                "class_name": control.get("class_name"),
                "role": control.get("role"),
                "bounds": bounds,
                "window_title": control.get("window_title"),
                "process_id": control.get("process_id") or control.get("pid"),
                "handle": control.get("handle"),
                "source": control.get("source"),
            }
        bounds = self._coerce_bounds(getattr(control, "bounds", None) or getattr(control, "bounding_box", None))
        return {
            "name": getattr(control, "name", None),
            "value": getattr(control, "value", None),
            "text": getattr(control, "text", None),
            "control_type": getattr(control, "control_type", None) or getattr(control, "type", None),
            "automation_id": getattr(control, "automation_id", None),
            "class_name": getattr(control, "class_name", None),
            "role": getattr(control, "role", None),
            "bounds": bounds,
            "window_title": getattr(control, "window_title", None),
            "process_id": getattr(control, "process_id", None) or getattr(control, "pid", None),
            "handle": getattr(control, "handle", None),
            "source": getattr(control, "source", None),
        }

    def _input_context_snapshot(self) -> dict[str, Any]:
        state = self._safe_backend_state()
        if state is None:
            return {"active_window": None, "focused_control": None}
        return {
            "active_window": self._window_to_snapshot(getattr(state, "active_window", None)),
            "focused_control": self._serialize_control(getattr(state, "focused_control", None)),
        }

    def _hit_test_element(self, x: int, y: int) -> dict[str, Any]:
        backend = self._backend
        if backend is None:
            return {"type": "unknown", "name": None, "found": False, "confidence": 0.0}

        def _node_attr(node: Any, key: str, default: Any = None) -> Any:
            if isinstance(node, dict):
                return node.get(key, default)
            return getattr(node, key, default)

        def _node_bounds(node: Any) -> dict[str, int] | None:
            return self._coerce_bounds(_node_attr(node, "bounding_box") or _node_attr(node, "bounds"))

        def _semantic_role(node: Any) -> str | None:
            text = " ".join(
                str(part or "").casefold()
                for part in (
                    _node_attr(node, "control_type"),
                    _node_attr(node, "role"),
                    _node_attr(node, "class_name"),
                    _node_attr(node, "name"),
                    _node_attr(node, "automation_id"),
                )
            )
            if any(token in text for token in ("document", "editor", "richedit", "text area", "textarea")):
                return "document"
            if any(token in text for token in ("edit", "textbox", "text box", "textinput")):
                return "text_input"
            if "button" in text:
                return "button"
            if any(token in text for token in ("list", "tree", "grid")):
                return "collection"
            return None

        def _node_meta(node: Any) -> dict[str, Any]:
            semantic_role = _semantic_role(node)
            bounds = _node_bounds(node)
            return {
                "type": _node_attr(node, "control_type", "unknown") or semantic_role or "unknown",
                "name": _node_attr(node, "name", None),
                "automation_id": _node_attr(node, "automation_id", None),
                "class_name": _node_attr(node, "class_name", None),
                "role": _node_attr(node, "role", None),
                "process_id": _node_attr(node, "process_id", None) or _node_attr(node, "pid", None),
                "window_title": _node_attr(node, "window_title", None),
                "semantic_role": semantic_role,
                "bounds": bounds,
            }

        def _is_decorative(node: Any) -> bool:
            control_type = (_node_attr(node, "control_type", "") or "").lower()
            role = (_node_attr(node, "role", "") or "").lower()
            class_name = (_node_attr(node, "class_name", "") or "").lower()
            name = (_node_attr(node, "name", "") or "").strip().lower()
            if any(token in " ".join((control_type, role, class_name)) for token in ("document", "edit", "richedit", "text")):
                return False
            if control_type in {"imagecontrol", "textcontrol", "panecontrol"} and not name:
                return True
            if role in {"image", "graphic", "separator", "static text"} and not _node_attr(node, "automation_id", None):
                return True
            return False

        def _score_node(node: Any, ancestry_depth: int, sibling_index: int, sibling_count: int) -> dict[str, Any] | None:
            bounds = _node_bounds(node)
            if bounds is None:
                return None
            left, top, right, bottom = bounds["left"], bounds["top"], bounds["right"], bounds["bottom"]
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
            has_children = bool(_node_attr(node, "children", None))
            leaf_bonus = 0.10 if not has_children else 0.0
            interactive_bonus = 0.14 if (_node_attr(node, "name", None) or _node_attr(node, "automation_id", None) or _node_attr(node, "role", None)) else 0.0
            specificity_bonus = 0.0
            semantic_role = _semantic_role(node)
            if _node_attr(node, "name", None):
                specificity_bonus += 0.05
            if _node_attr(node, "automation_id", None):
                specificity_bonus += 0.10
            if _node_attr(node, "class_name", None):
                specificity_bonus += 0.04
            if _node_attr(node, "role", None):
                specificity_bonus += 0.04
            if semantic_role == "document":
                specificity_bonus += 0.10
            elif semantic_role == "text_input":
                specificity_bonus += 0.08
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
            }

        def _iter_candidate_entries(state: Any) -> list[tuple[Any, int, int, int]]:
            entries: list[tuple[Any, int, int, int]] = []
            seen: set[int] = set()

            def _collect_group(nodes: list[Any], depth: int) -> None:
                sibling_count = len(nodes)
                for index, node in enumerate(nodes):
                    if node is None:
                        continue
                    identity = id(node)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    entries.append((node, depth, index, sibling_count))
                    children = _node_attr(node, "children", None)
                    if children:
                        _collect_group(list(children), depth + 1)

            groups = []
            for attr_name in ("interactive_nodes", "tree_nodes", "nodes", "children"):
                group = getattr(state, attr_name, None)
                if group:
                    groups.append(list(group))
            for group in groups:
                _collect_group(group, depth=0)
            return entries

        def _best_from_nodes(state: Any) -> dict[str, Any] | None:
            entries = _iter_candidate_entries(state)
            if not entries:
                return None
            scored: list[tuple[float, int, dict[str, Any]]] = []
            for node, depth, idx, sibling_count in entries:
                candidate = _score_node(node, ancestry_depth=depth, sibling_index=idx, sibling_count=sibling_count)
                if candidate is None:
                    continue
                scored.append((candidate["confidence"], -idx, candidate))
            if not scored:
                return None
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return scored[0][2]

        def _control_fallback(control: Any, source: str) -> dict[str, Any] | None:
            snapshot = self._serialize_control(control)
            if snapshot is None or not self._point_within_bounds(x, y, snapshot.get("bounds")):
                return None
            element = {
                "type": snapshot.get("control_type") or "unknown",
                "name": snapshot.get("name"),
                "automation_id": snapshot.get("automation_id"),
                "class_name": snapshot.get("class_name"),
                "role": snapshot.get("role"),
                "process_id": snapshot.get("process_id"),
                "window_title": snapshot.get("window_title"),
                "semantic_role": _semantic_role(snapshot),
                "bounds": snapshot.get("bounds"),
                "found": True,
                "confidence": 0.42 if source == "focused_control" else 0.34,
                "z_index": 0,
                "ancestry_depth": 0,
                "source": source,
            }
            return element

        tree_state = getattr(backend, "get_tree_state", None)
        if callable(tree_state):
            try:
                state = tree_state()
            except Exception:
                state = None
            if state is not None:
                best = _best_from_nodes(state)
                if best is not None:
                    best["source"] = "tree_state"
                    return best

        state = self._safe_backend_state()
        if state is not None:
            tree_state_obj = getattr(state, "tree_state", None)
            if tree_state_obj is not None:
                best = _best_from_nodes(tree_state_obj)
                if best is not None:
                    best["source"] = "snapshot"
                    return best
            focused_fallback = _control_fallback(getattr(state, "focused_control", None), "focused_control")
            if focused_fallback is not None:
                return focused_fallback
            active_fallback = _control_fallback(getattr(state, "active_window", None), "active_window")
            if active_fallback is not None:
                return active_fallback

        return {"type": "unknown", "name": None, "found": False, "confidence": 0.0}

    def _motion_steps_for_kind(self, kind: str, steps: int) -> int:
        if kind == "hover":
            return max(4, min(10, steps))
        if kind == "click":
            return max(2, min(4, steps))
        if kind == "drag":
            return max(8, steps)
        if kind == "move":
            return max(6, steps)
        return max(2, steps)

    def _virtual_mouse_motion(
        self,
        kind: str,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int | None = None,
        steps: int = 16,
        hover_ms: int = 0,
        jitter_px: int = 0,
        accel: float = 1.0,
        decel: float = 1.0,
    ) -> dict[str, Any]:
        steps = self._motion_steps_for_kind(kind, steps)
        action = self._motion_scheduler.plan(kind=kind, start=start, end=end, duration_ms=duration_ms, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel)
        result = self._motion_scheduler.run(action, steps=steps)
        self._overlay_renderer.update_cursor(end[0], end[1])
        self._overlay_renderer.attach_motion(result.phase.value, {"kind": kind, "steps": len(result.path), "hover_ms": hover_ms, "jitter_px": jitter_px, "accel": accel, "decel": decel, "duration_ms": result.action.duration_ms})
        overlay_snapshot = self._overlay_renderer.snapshot()
        return {
            "motion": {
                "ok": result.ok,
                "phase": result.phase.value,
                "action": {
                    "kind": result.action.kind,
                    "start": {"x": result.action.start.x, "y": result.action.start.y},
                    "end": {"x": result.action.end.x, "y": result.action.end.y},
                    "duration_ms": result.action.duration_ms,
                    "easing": result.action.easing,
                    "hover_ms": result.action.hover_ms,
                    "jitter_px": result.action.jitter_px,
                    "accel": result.action.accel,
                    "decel": result.action.decel,
                    "metadata": result.action.metadata,
                },
                "path": [{"x": point.x, "y": point.y, "t": point.t} for point in result.path],
                "detail": result.detail,
                "metadata": result.metadata,
            },
            "overlay_state": {
                "visible": overlay_snapshot.visible,
                "cursor_x": overlay_snapshot.cursor_x,
                "cursor_y": overlay_snapshot.cursor_y,
                "trail": [list(point) for point in overlay_snapshot.trail],
                "metadata": overlay_snapshot.metadata,
            },
        }

    def _verify_click_target(self, before_context: dict[str, Any], after_context: dict[str, Any], *, element: dict[str, Any] | None, button: str, clicks: int) -> dict[str, Any]:
        before_focus = before_context.get("focused_control")
        after_focus = after_context.get("focused_control")
        before_window = before_context.get("active_window")
        after_window = after_context.get("active_window")
        focus_changed = before_focus != after_focus
        window_changed = before_window != after_window
        ok = focus_changed or window_changed or element is not None
        return {
            "ok": ok,
            "reason": "focus_changed" if focus_changed else ("window_changed" if window_changed else "element_targeted"),
            "before": {"active_window": before_window, "focused_control": before_focus},
            "after": {"active_window": after_window, "focused_control": after_focus},
            "focus_changed": focus_changed,
            "window_changed": window_changed,
            "element": element,
            "button": button,
            "clicks": clicks,
        }

    def _verify_drag_target(self, before_context: dict[str, Any], after_context: dict[str, Any], *, start: tuple[int, int], end: tuple[int, int]) -> dict[str, Any]:
        before_focus = before_context.get("focused_control")
        after_focus = after_context.get("focused_control")
        before_window = before_context.get("active_window")
        after_window = after_context.get("active_window")
        focus_changed = before_focus != after_focus
        window_changed = before_window != after_window
        ok = after_window is not None and (window_changed or focus_changed or after_focus is not None)
        return {
            "ok": ok,
            "reason": "window_changed" if window_changed else ("focus_changed" if focus_changed else "state_read"),
            "before": {"active_window": before_window, "focused_control": before_focus},
            "after": {"active_window": after_window, "focused_control": after_focus},
            "focus_changed": focus_changed,
            "window_changed": window_changed,
            "start": {"x": start[0], "y": start[1]},
            "end": {"x": end[0], "y": end[1]},
        }

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1, hover_ms: int = 80, jitter_px: int = 1) -> InputResult:
        def runner() -> InputResult:
            before_context = self._input_context_snapshot()
            element = self._hit_test_element(x, y)
            hover_motion = self._virtual_mouse_motion("hover", (self._motion_scheduler.cursor_state.x, self._motion_scheduler.cursor_state.y), (x, y), steps=6, hover_ms=hover_ms, jitter_px=jitter_px, accel=0.8, decel=1.2)
            settle_motion = self._virtual_mouse_motion("move", (x, y), (x, y), steps=3, hover_ms=hover_ms, jitter_px=jitter_px, accel=0.9, decel=1.1)
            virtual_mouse = self._virtual_mouse_motion("click", (x, y), (x, y), steps=3, hover_ms=hover_ms, jitter_px=jitter_px, accel=1.0, decel=1.0)
            payload = {"x": x, "y": y, "button": button, "clicks": clicks, "element": element, "pre_click_hover": hover_motion, "pre_click_settle": settle_motion, **virtual_mouse}
            self._overlay_renderer.show()
            self._overlay_renderer.update_cursor(x, y)
            self._overlay_renderer.draw_click_ripple(x, y, radius=max(14, 12 + clicks * 4))
            if self._backend is None:
                after_context = self._input_context_snapshot()
                payload["target_verification"] = self._verify_click_target(before_context, after_context, element=element, button=button, clicks=clicks)
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                return self._result("input_click", f"clicked:{x},{y}:{button}:{clicks}", ok=bool(payload["target_verification"].get("ok", True)), payload=payload, tool="input_click")

            if hasattr(self._backend, "move"):
                self._backend.move((x, y))
            if hasattr(self._backend, "click"):
                self._overlay_renderer.record_timeline("click_down", {"at": datetime.now(timezone.utc).isoformat(), "kind": "click", "phase": "down", "x": x, "y": y, "button": button, "clicks": clicks})
                self._backend.click((x, y), button=button, clicks=clicks)
                self._overlay_renderer.record_timeline("click_up", {"at": datetime.now(timezone.utc).isoformat(), "kind": "click", "phase": "up", "x": x, "y": y, "button": button, "clicks": clicks})
                after_context = self._input_context_snapshot()
                payload["target_verification"] = self._verify_click_target(before_context, after_context, element=element, button=button, clicks=clicks)
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                return self._result("input_click", f"clicked:{x},{y}:{button}:{clicks}", ok=bool(payload["target_verification"].get("ok", True)), payload=payload, tool="input_click")

            raise ExecutorError("Backend does not expose click().")

        return self._run_input_with_recovery(operation="click", runner=runner)

    def move(self, x: int, y: int, steps: int = 8, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0) -> InputResult:
        def runner() -> InputResult:
            motion = self._virtual_mouse_motion("move", (self._motion_scheduler.cursor_state.x, self._motion_scheduler.cursor_state.y), (x, y), steps=steps, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel)
            payload = {"x": x, "y": y, "element": self._hit_test_element(x, y), **motion}
            self._overlay_renderer.show()
            self._overlay_renderer.update_cursor(x, y)
            self._overlay_renderer.attach_motion(motion.get("phase", "move"), {"kind": "move", "steps": len(motion.get("path", [])), "hover_ms": hover_ms, "jitter_px": jitter_px, "accel": accel, "decel": decel, "last_target": {"x": x, "y": y}})
            if self._backend is None:
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                payload["target_verification"] = {"ok": True, "reason": "synthetic_backend"}
                return self._result("move", f"moved:{x},{y}", payload=payload, tool="input_move")

            if hasattr(self._backend, "move"):
                self._backend.move((x, y))
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                payload["target_verification"] = {"ok": True, "reason": "cursor_reached"}
                return self._result("move", f"moved:{x},{y}", payload=payload, tool="input_move")

            raise ExecutorError("Backend does not expose move().")

        return self._run_input_with_recovery(operation="move", runner=runner)

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 16, hover_ms: int = 120, jitter_px: int = 1, accel: float = 1.0, decel: float = 1.1) -> InputResult:
        def runner() -> InputResult:
            before_context = self._input_context_snapshot()
            hover_motion = self._virtual_mouse_motion("hover", (self._motion_scheduler.cursor_state.x, self._motion_scheduler.cursor_state.y), start, steps=6, hover_ms=hover_ms, jitter_px=jitter_px, accel=0.8, decel=1.2)
            virtual_mouse = self._virtual_mouse_motion("drag", start, end, steps=steps, hover_ms=hover_ms, jitter_px=jitter_px, accel=accel, decel=decel)
            payload = {
                "start": {"x": start[0], "y": start[1], "element": self._hit_test_element(start[0], start[1])},
                "end": {"x": end[0], "y": end[1], "element": self._hit_test_element(end[0], end[1])},
                "active_window_before": before_context["active_window"],
                "focused_control_before": before_context["focused_control"],
                "pre_drag_hover": hover_motion,
                **virtual_mouse,
            }
            self._overlay_renderer.show()
            self._overlay_renderer.record_timeline("drag_prepare", {"at": datetime.now(timezone.utc).isoformat(), "kind": "drag", "phase": "prepare", "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}})
            self._overlay_renderer.set_drag_state(True, start={"x": start[0], "y": start[1]})
            self._overlay_renderer.update_cursor(start[0], start[1])
            if self._backend is None:
                self._overlay_renderer.update_cursor(end[0], end[1])
                self._overlay_renderer.set_drag_state(False, start={"x": start[0], "y": start[1]})
                payload["target_verification"] = self._verify_drag_target(before_context, before_context, start=start, end=end)
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", ok=bool(payload["target_verification"].get("ok", True)), payload=payload, tool="input_drag")

            if hasattr(self._backend, "move") and hasattr(self._backend, "drag"):
                self._backend.move(start)
                if hasattr(self._backend, "mouse_down"):
                    self._backend.mouse_down(start)
                self._overlay_renderer.record_timeline("drag_down", {"at": datetime.now(timezone.utc).isoformat(), "kind": "drag", "phase": "down", "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}})
                self._backend.drag(end)
                if hasattr(self._backend, "mouse_up"):
                    self._backend.mouse_up(end)
                self._overlay_renderer.record_timeline("drag_up", {"at": datetime.now(timezone.utc).isoformat(), "kind": "drag", "phase": "up", "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}})
                after_context = self._input_context_snapshot()
                payload["active_window_after"] = after_context["active_window"]
                payload["focused_control_after"] = after_context["focused_control"]
                payload["target_verification"] = self._verify_drag_target(before_context, after_context, start=start, end=end)
                self._overlay_renderer.update_cursor(end[0], end[1])
                self._overlay_renderer.set_drag_state(False, start={"x": start[0], "y": start[1]})
                payload["overlay_state"] = self._overlay_snapshot_payload()
                payload["execution_timeline"] = self._overlay_snapshot_payload().get("timeline", [])
                return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", ok=bool(payload["target_verification"].get("ok", True)), payload=payload, tool="input_drag")

            self._overlay_renderer.set_drag_state(False, start={"x": start[0], "y": start[1]})
            raise ExecutorError("Backend does not expose drag support.")

        return self._run_input_with_recovery(operation="drag", runner=runner)

    def type_text(
        self,
        text: str,
        press_enter: bool = False,
        clear: bool = False,
        caret_position: str = "idle",
    ) -> InputResult:
        def runner() -> InputResult:
            if self._backend is None:
                suffix = ":enter" if press_enter else ""
                payload = {
                    "text": text,
                    "press_enter": press_enter,
                    "clear": clear,
                    "caret_position": caret_position,
                    "validation": {"passed": True, "expected_change": False, "changed": None},
                }
                self._overlay_renderer.attach_motion("typing", {"kind": "type", "last_target": None})
                payload["overlay_state"] = self._overlay_snapshot_payload()
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
            self._overlay_renderer.show()
            self._overlay_renderer.attach_motion("typing", {"kind": "type", "last_target": {"x": type_loc[0], "y": type_loc[1]}})
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
            payload["overlay_state"] = self._overlay_snapshot_payload()
            return self._result("input_type", detail, ok=validation_passed, payload=payload, tool="input_type")

        raise ExecutorError("Backend does not expose type().")

    def multi_select(self, coordinates: list[tuple[int, int]], press_ctrl: bool = False) -> InputResult:
        before_context = self._input_context_snapshot()
        items = [{"x": x, "y": y, "element": self._hit_test_element(x, y)} for x, y in coordinates]
        payload = {
            "count": len(coordinates),
            "press_ctrl": press_ctrl,
            "targets": items,
            "active_window_before": before_context["active_window"],
            "focused_control_before": before_context["focused_control"],
        }
        if self._backend is None:
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload=payload,
                tool="input_multi_select",
            )

        if hasattr(self._backend, "multi_select"):
            self._backend.multi_select(press_ctrl=press_ctrl, locs=coordinates)
            after_context = self._input_context_snapshot()
            payload["active_window_after"] = after_context["active_window"]
            payload["focused_control_after"] = after_context["focused_control"]
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload=payload,
                tool="input_multi_select",
            )

        raise ExecutorError("Backend does not expose multi_select().")

    def multi_edit(self, edits: list[tuple[int, int, str]]) -> InputResult:
        before_context = self._input_context_snapshot()
        items = [{"x": x, "y": y, "text": text, "element": self._hit_test_element(x, y)} for x, y, text in edits]
        payload = {
            "count": len(edits),
            "items": items,
            "active_window_before": before_context["active_window"],
            "focused_control_before": before_context["focused_control"],
        }
        if self._backend is None:
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload=payload, tool="input_multi_edit")

        if hasattr(self._backend, "multi_edit"):
            self._backend.multi_edit(edits)
            after_context = self._input_context_snapshot()
            payload["active_window_after"] = after_context["active_window"]
            payload["focused_control_after"] = after_context["focused_control"]
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload=payload, tool="input_multi_edit")

        raise ExecutorError("Backend does not expose multi_edit().")

    def shortcut(self, keys: str) -> InputResult:
        def runner() -> InputResult:
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
                        "injection_result": {"status": "sent", "method": "backend.shortcut.synthetic"},
                        "overlay_state": self._overlay_snapshot_payload(),
                    },
                    tool="input_shortcut",
                )

            if not hasattr(self._backend, "shortcut"):
                raise ExecutorError("Backend does not expose shortcut().")

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
                "overlay_state": self._overlay_snapshot_payload(),
            }
            return self._result("input_shortcut", f"shortcut:{keys}", payload=payload, tool="input_shortcut")

        return self._run_input_with_recovery(operation="shortcut", runner=runner)

    def scroll(self, direction: str, amount: int = 1) -> InputResult:
        before_context = self._input_context_snapshot()
        payload = {
            "direction": direction,
            "amount": amount,
            "target_window_before": before_context["active_window"],
            "target_control_before": before_context["focused_control"],
        }
        if self._backend is None:
            return self._result("scroll", f"scrolled:{direction}:{amount}", payload=payload, tool="input_scroll")

        if hasattr(self._backend, "scroll"):
            self._backend.scroll(direction=direction, wheel_times=amount)
            after_context = self._input_context_snapshot()
            payload["target_window_after"] = after_context["active_window"]
            payload["target_control_after"] = after_context["focused_control"]
            return self._result("scroll", f"scrolled:{direction}:{amount}", payload=payload, tool="input_scroll")

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
            request_variants = self._launch_name_variants(requested_target)
            normalized_key = request_variants[0] if request_variants else requested_target.lower()
            matched_target = alias_map.get(normalized_key, [self._strip_launch_noise(requested_target) or requested_target])[0]
            discovered_target, discovery = self._discover_launch_path(requested_target, alias_map)
            effective_target = discovered_target or matched_target
            resolved_alias = effective_target if effective_target != requested_target else None

            verification_aliases = {
                "explorer.exe": ["explorer", "file explorer", "文件资源管理器"],
                "calc.exe": ["calc", "calculator", "计算器"],
                "notepad.exe": ["notepad", "记事本"],
                "mspaint.exe": ["mspaint", "paint", "画图"],
            }
            verification_blacklist = {
                "calc.exe": {"mpicalc"},
            }

            def _normalized_text(value: Any) -> str:
                text = str(value or "").strip().lower()
                text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", text)
                return re.sub(r"\s+", " ", text).strip()

            expected_targets = set(self._launch_name_variants(requested_target))
            expected_targets.update(self._launch_name_variants(matched_target))
            expected_targets.update(self._launch_name_variants(effective_target))
            expected_phrases = {_normalized_text(item) for item in expected_targets}
            for alias in verification_aliases.get(matched_target.lower(), []):
                expected_targets.update(self._launch_name_variants(alias))
            if discovery is not None:
                expected_targets.update(self._launch_name_variants(discovery.get("display_name") or ""))
                expected_targets.update(self._launch_name_variants(discovery.get("resolved_target_path") or ""))

            expected_phrases.update({_normalized_text(item) for item in expected_targets})

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
                candidate_targets = set(self._launch_name_variants(str(candidate)))
                if candidate_targets.intersection(blacklisted_targets):
                    return False
                if candidate_targets.intersection(expected_targets):
                    return True
                candidate_words = normalized_candidate.split()
                if set(candidate_words).intersection(expected_targets):
                    return True
                for phrase in expected_phrases:
                    phrase_words = phrase.split()
                    if phrase_words and _contains_phrase_tokens(candidate_words, phrase_words):
                        return True
                return False

            def _extract_verification_hint(value: Any) -> tuple[str | None, str | None]:
                text = str(value or "")
                match = re.search(r"verification=(name|process|pid|phrase):([^\]\r\n]+)", text, flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip().lower(), match.group(2).strip()
                return None, None

            def _window_identity(snapshot: dict[str, Any]) -> tuple[Any, ...]:
                handle = snapshot.get("handle")
                if handle is not None:
                    return ("handle", handle)
                window_pid = snapshot.get("pid")
                normalized_name = self._normalize_window_name(snapshot.get("name") or snapshot.get("window_title"))
                if window_pid is not None:
                    return ("pid", window_pid, normalized_name)
                bounds = snapshot.get("bounds")
                bounds_key = tuple(bounds) if isinstance(bounds, (list, tuple)) else None
                return ("name", normalized_name, bounds_key)

            before_state = None
            after_state = None
            try:
                _, before_state = self._snapshot_launch_state()
            except Exception:
                before_state = None

            response = self._backend.launch_app(effective_target)
            response_text = response[0] if isinstance(response, tuple) and response else response
            status = response[1] if isinstance(response, tuple) and len(response) > 1 and isinstance(response[1], int) else None
            pid = response[2] if isinstance(response, tuple) and len(response) > 2 and isinstance(response[2], int) else None
            launched = status == 0 if status is not None else bool(response)
            verification_source, verification_hint = _extract_verification_hint(response_text)
            detected = False
            detected_name = None
            verification_attempts: list[dict[str, Any]] = []
            poll_attempt_count = 1 if (pid is not None and pid > 0 and launched) else 4
            try:
                for attempt in range(poll_attempt_count):
                    if attempt > 0:
                        time.sleep(0.35)
                    active_after, current_windows = self._snapshot_launch_state()
                    after_state = current_windows
                    before_count = len(before_state) if isinstance(before_state, list) else None
                    after_count = len(after_state) if isinstance(after_state, list) else None
                    window_count_increased = bool(before_count is not None and after_count is not None and after_count > before_count)
                    current_name = None
                    if isinstance(active_after, dict):
                        current_name = active_after.get("name") or active_after.get("window_title")
                    elif active_after is not None:
                        current_name = getattr(active_after, "name", None) or getattr(active_after, "window_title", None)

                    matched_this_attempt = _matches_expected(current_name)
                    verification_attempts.append(
                        {
                            "attempt": attempt + 1,
                            "window_count_increased": window_count_increased,
                            "detected_window_name": current_name,
                            "verification_source": verification_source,
                            "target_matches": matched_this_attempt,
                        }
                    )
                    if current_name:
                        detected_name = current_name
                    detected = bool(detected or window_count_increased or matched_this_attempt)
                    if matched_this_attempt:
                        break
            except Exception:
                after_state = None

            before_windows = [self._window_to_snapshot(window) for window in (before_state or [])]
            before_windows = [window for window in before_windows if window is not None]
            after_windows = [self._window_to_snapshot(window) for window in (after_state or [])]
            after_windows = [window for window in after_windows if window is not None]

            before_matching_windows = [
                window
                for window in before_windows
                if _matches_expected(window.get("name") or window.get("window_title"))
            ]
            after_matching_windows = [
                window
                for window in after_windows
                if _matches_expected(window.get("name") or window.get("window_title"))
            ]
            before_window_identities = {_window_identity(window) for window in before_windows}
            new_visible_windows = [
                window for window in after_windows if _window_identity(window) not in before_window_identities
            ]
            new_matching_windows = [
                window
                for window in new_visible_windows
                if _matches_expected(window.get("name") or window.get("window_title"))
                or (pid is not None and pid > 0 and window.get("pid") == pid)
            ]

            backend_verification_matches = _matches_expected(verification_hint)
            matched_window_name = None
            if new_matching_windows:
                matched_window_name = new_matching_windows[0].get("name") or new_matching_windows[0].get("window_title")
            elif after_matching_windows:
                matched_window_name = after_matching_windows[0].get("name") or after_matching_windows[0].get("window_title")

            resolved_detected_name = matched_window_name or (verification_hint if backend_verification_matches else detected_name)
            target_matches = _matches_expected(resolved_detected_name) or backend_verification_matches
            before_window_count = len(before_state) if isinstance(before_state, list) else None
            after_window_count = len(after_state) if isinstance(after_state, list) else None
            new_instance_inferred = bool(
                not new_matching_windows
                and target_matches
                and isinstance(before_window_count, int)
                and isinstance(after_window_count, int)
                and after_window_count > before_window_count
            )
            new_instance_detected = bool(new_matching_windows or new_instance_inferred)
            mismatch_signals = [
                candidate
                for candidate in (resolved_detected_name, None if backend_verification_matches else verification_hint)
                if candidate is not None and str(candidate).strip() and not _matches_expected(candidate)
            ]
            backend_failed_but_verified = bool((status not in (None, 0) or not pid) and target_matches)
            backend_verified_success = bool(launched and verification_source in {"process", "pid", "phrase", "name"} and backend_verification_matches)
            verification_evidence = bool(
                target_matches
                or detected
                or (pid is not None and pid > 0)
                or (response_text is not None and str(response_text).strip())
            )
            verification_ok = bool(backend_verified_success or (launched and target_matches) or backend_failed_but_verified)
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
                else (f"launch pending verification:{name}" if partial_ok else (f"launch failed:{name}" if not launched else f"target mismatch:{name}->{resolved_detected_name}"))
            )
            if target_matches and not any(attempt.get("target_matches") for attempt in verification_attempts):
                verification_attempts.append(
                    {
                        "attempt": len(verification_attempts) + 1,
                        "window_count_increased": bool(
                            before_window_count is not None
                            and after_window_count is not None
                            and after_window_count > before_window_count
                        ),
                        "detected_window_name": resolved_detected_name,
                        "verification_source": "window_list" if matched_window_name else (verification_source or "derived"),
                        "target_matches": True,
                    }
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
                "before_window_count": before_window_count,
                "after_window_count": after_window_count,
                "matching_instance_count_before": len(before_matching_windows),
                "matching_instance_count_after": len(after_matching_windows),
                "new_instance_detected": new_instance_detected,
                "new_instance_handles": [window.get("handle") for window in new_matching_windows if window.get("handle") is not None],
                "new_instance_pids": [window.get("pid") for window in new_matching_windows if window.get("pid") is not None],
                "window_detected": detected,
                "detected_window_name": resolved_detected_name,
                "verification_source": verification_source,
                "verification_hint": verification_hint,
                "matched_window_name": matched_window_name,
                "verification_attempts": verification_attempts,
                "target_matches": target_matches,
                "verification_status": verification_status,
                "result_code": result_code,
                "warning": None if verification_ok else ("launch outcome could not be fully verified against the requested target" if partial_ok else "launch outcome could not be verified against the requested target"),
            }
            return self._result("input_launch_app", detail, ok=(verification_ok or partial_ok), payload=payload, tool="input_launch_app")

        raise ExecutorError("Backend does not expose launch_app().")

    @staticmethod
    def _normalize_window_name(value: Any) -> str:
        if value is None:
            return ""
        normalized = re.sub(r"\s+", " ", str(value)).strip().casefold()
        normalized = re.sub(r"^[*•●\s]+", "", normalized)
        return normalized.strip()

    def _window_name_candidates(self, snapshot: dict[str, Any] | None) -> set[str]:
        if snapshot is None:
            return set()
        candidates: set[str] = set()
        for key in ("name", "window_title"):
            normalized = self._normalize_window_name(snapshot.get(key))
            if normalized:
                candidates.add(normalized)
        return candidates

    @staticmethod
    def _window_status(snapshot: dict[str, Any] | None) -> str:
        if snapshot is None:
            return ""
        return str(snapshot.get("status") or "").strip().casefold()

    def _window_is_minimized(self, snapshot: dict[str, Any] | None) -> bool:
        return self._window_status(snapshot).endswith("minimized")

    def _window_is_maximized(self, snapshot: dict[str, Any] | None) -> bool:
        return self._window_status(snapshot).endswith("maximized")

    @staticmethod
    def _window_same_target(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
        if left is None or right is None:
            return False
        left_handle = left.get("handle")
        right_handle = right.get("handle")
        if left_handle is not None and right_handle is not None:
            return left_handle == right_handle
        left_pid = left.get("pid")
        right_pid = right.get("pid")
        if left_pid is not None and right_pid is not None:
            return left_pid == right_pid
        return False

    def _window_bounds_area(self, snapshot: dict[str, Any] | None) -> int | None:
        if snapshot is None:
            return None
        bounds = snapshot.get("bounds")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
            return None
        left, top, right, bottom = bounds
        try:
            return max(0, int(right) - int(left)) * max(0, int(bottom) - int(top))
        except Exception:
            return None

    def _resolve_target_window(
        self,
        *,
        name: str | None = None,
        handle: int | None = None,
        pid: int | None = None,
        refresh: bool = False,
        prefer_active: bool = False,
    ) -> tuple[dict[str, Any] | None, str]:
        matched_by = "active"
        if handle is not None:
            matched_by = "handle"
        elif pid is not None:
            matched_by = "pid"
        elif name:
            matched_by = "name"
        return (
            self._find_window_snapshot(name=name, handle=handle, pid=pid, refresh=refresh, prefer_active=prefer_active),
            matched_by,
        )

    def _poll_window_observations(
        self,
        *,
        name: str | None = None,
        handle: int | None = None,
        pid: int | None = None,
        prefer_active: bool = False,
        attempts: int = 5,
        delay: float = 0.1,
    ) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for index in range(max(1, attempts)):
            visible = self._snapshot_windows(refresh=True)
            active = visible[0] if visible else None
            target = self._find_window_snapshot(
                name=name,
                handle=handle,
                pid=pid,
                refresh=False,
                prefer_active=prefer_active,
                include_history=False,
            )
            observations.append({"target": target, "active": active, "visible": visible})
            if index + 1 < attempts:
                time.sleep(delay)
        return observations

    def _user32(self) -> Any | None:
        try:
            return ctypes.windll.user32
        except Exception:
            return None

    def _window_handle_exists(self, handle: int | None) -> bool:
        if handle is None:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            return bool(user32.IsWindow(int(handle)))
        except Exception:
            return False

    def _native_focus_window(self, handle: int | None) -> bool:
        if handle is None:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return False
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            else:
                user32.ShowWindow(hwnd, 5)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def _native_show_window(self, handle: int | None, command: int) -> bool:
        if handle is None:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return False
            user32.ShowWindow(hwnd, int(command))
            return True
        except Exception:
            return False

    def _native_is_iconic(self, handle: int | None) -> bool | None:
        if handle is None:
            return None
        user32 = self._user32()
        if user32 is None:
            return None
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return None
            return bool(user32.IsIconic(hwnd))
        except Exception:
            return None

    def _native_is_zoomed(self, handle: int | None) -> bool | None:
        if handle is None:
            return None
        user32 = self._user32()
        if user32 is None:
            return None
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return None
            return bool(user32.IsZoomed(hwnd))
        except Exception:
            return None

    def _native_window_rect(self, handle: int | None) -> dict[str, int] | None:
        if handle is None:
            return None
        user32 = self._user32()
        if user32 is None:
            return None
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return None
            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
            return {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
        except Exception:
            return None

    def _native_move_window(self, handle: int | None, x: int | None, y: int | None, width: int | None, height: int | None) -> bool:
        if handle is None or None in {x, y, width, height}:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return False
            return bool(user32.MoveWindow(hwnd, int(x), int(y), int(width), int(height), True))
        except Exception:
            return False

    def _native_restore_window(self, handle: int | None) -> bool:
        if handle is None:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return False
            user32.ShowWindow(hwnd, 9)
            user32.BringWindowToTop(hwnd)
            return True
        except Exception:
            return False

    def _native_close_window(self, handle: int | None) -> bool:
        if handle is None:
            return False
        user32 = self._user32()
        if user32 is None:
            return False
        try:
            hwnd = int(handle)
            if not user32.IsWindow(hwnd):
                return False
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
            return True
        except Exception:
            return False

    def switch_window(self, name: str, handle: int | None = None, pid: int | None = None) -> InputResult:
        previous = self._snapshot_window(refresh=True)
        target_before, matched_by = self._resolve_target_window(name=name, handle=handle, pid=pid, refresh=True, prefer_active=True)
        target_label = (target_before or {}).get("name") or name
        if self._backend is None:
            return self._result(
                "window_switch",
                f"switch:{name}",
                payload={
                    **self._window_payload(target_window=target_label, before=previous, after={"name": target_label, "status": None, "handle": handle}),
                    "previous_window": previous.get("name") if previous else None,
                    "previous_handle": previous.get("handle") if previous else None,
                    "current_window": target_label,
                    "current_handle": handle,
                    "matched_by": matched_by,
                    "restored_from_minimized": False,
                    "verified": False,
                },
                tool="window_switch",
            )

        if hasattr(self._backend, "switch_app"):
            response = self._backend.switch_app(target_label)
            detail, status = self._normalize_backend_response(response)
            current, current_matched_by = self._resolve_target_window(
                name=name,
                handle=handle or (target_before or {}).get("handle"),
                pid=pid or (target_before or {}).get("pid"),
                refresh=True,
                prefer_active=True,
            )
            if current is None:
                current = self._snapshot_window(refresh=True)
            observed_match = bool(
                current
                and (
                    self._window_name_matches(current, name)
                    or self._window_same_target(current, target_before)
                    or (handle is not None and current.get("handle") == handle)
                    or (pid is not None and current.get("pid") == pid)
                )
            )
            previous_already_target = bool(
                previous
                and (
                    self._window_name_matches(previous, name)
                    or self._window_same_target(previous, target_before)
                    or (handle is not None and previous.get("handle") == handle)
                    or (pid is not None and previous.get("pid") == pid)
                )
            )
            observed_recovery = bool(observed_match and not previous_already_target)
            verified = bool((status in (None, 0) and observed_match) or observed_recovery)
            result_detail = detail
            backend_response = response
            backend_response_detail = detail
            backend_response_code = status
            if verified and status not in (None, 0):
                resolved_name = current.get("name") if current else None
                result_detail = f"Switched to {resolved_name or target_label} window."
                backend_response = (result_detail, 0)
                backend_response_detail = result_detail
                backend_response_code = 0
            restored_from_minimized = self._window_is_minimized(target_before)
            payload = {
                **self._window_payload(target_window=target_label, before=previous, after=current),
                "name": name,
                "previous_window": previous.get("name") if previous else None,
                "previous_handle": previous.get("handle") if previous else None,
                "current_window": current.get("name") if current else None,
                "current_handle": current.get("handle") if current else None,
                "matched_by": current_matched_by,
                "restored_from_minimized": restored_from_minimized,
                "backend_response": backend_response,
                "backend_response_detail": backend_response_detail,
                "backend_response_code": backend_response_code,
                "verified": verified,
            }
            if verified and status not in (None, 0):
                payload["switch_backend_response"] = response
                payload["switch_backend_response_detail"] = detail
                payload["switch_backend_response_code"] = status
            return self._result("window_switch", result_detail, ok=verified, payload=payload, tool="window_switch")

        raise ExecutorError("Backend does not expose switch_app().")

    def focus_window(self, name: str, handle: int | None = None, pid: int | None = None) -> InputResult:
        active = self._ensure_window_ready(name=name, handle=handle, pid=pid)
        if self._backend is None:
            payload = self._window_payload(target_window=name, before={"name": name, "status": None, "handle": handle, "pid": pid}, after=active, verified=False)
            payload["overlay_state"] = self._overlay_snapshot_payload()
            return self._result("window_focus", f"focus:{name}", payload=payload, tool="window_focus")

        if hasattr(self._backend, "focus_app"):
            previous = self._snapshot_window(refresh=True)
            visible_before = self._snapshot_windows(refresh=False)
            target_before, matched_by = self._resolve_target_window(name=name, handle=handle, pid=pid, refresh=True, prefer_active=True)
            target_label = (target_before or {}).get("name") or name
            target_handle = handle or (target_before or {}).get("handle")
            target_pid = pid or (target_before or {}).get("pid")
            target_visible_before = bool(target_handle is not None and any(window.get("handle") == target_handle for window in visible_before))
            restored_from_minimized = self._window_is_minimized(target_before)

            response: Any
            detail: str
            status: int | None
            strategy = "focus_app"
            native_used = False
            if target_handle is not None and (restored_from_minimized or not target_visible_before):
                native_used = self._native_focus_window(target_handle)
            if native_used:
                detail = f"Focused {target_label or target_handle} via native handle fallback."
                status = 0
                response = (detail, 0)
                strategy = "native_handle"
            else:
                response = self._backend.focus_app(target_label)
                detail, status = self._normalize_backend_response(response)

            current, current_matched_by = self._resolve_target_window(
                name=name,
                handle=target_handle,
                pid=target_pid,
                refresh=True,
                prefer_active=True,
            )
            active_after = self._snapshot_window(refresh=True)
            verified = bool(
                status in (None, 0)
                and current
                and active_after
                and (
                    self._window_same_target(active_after, current)
                    or self._window_name_matches(active_after, name)
                    or (target_handle is not None and active_after.get("handle") == target_handle)
                    or (target_pid is not None and active_after.get("pid") == target_pid)
                )
            )
            result = self._result(
                "window_focus",
                detail,
                ok=verified,
                payload={
                    **self._window_payload(target_window=target_label, before=previous, after=current),
                    "name": name,
                    "previous_window": previous.get("name") if previous else None,
                    "previous_handle": previous.get("handle") if previous else None,
                    "current_window": current.get("name") if current else None,
                    "current_handle": current.get("handle") if current else None,
                    "active_window_after": active_after,
                    "matched_by": current_matched_by or matched_by,
                    "restored_from_minimized": restored_from_minimized,
                    "backend_response": response,
                    "backend_response_detail": detail,
                    "backend_response_code": status,
                    "verified": verified,
                    "strategy": strategy,
                    "overlay_state": self._overlay_snapshot_payload(),
                },
                tool="window_focus",
            )

            if not verified and strategy == "focus_app":
                fallback = self.switch_window(name, handle=handle, pid=pid)
                if fallback.payload is None:
                    fallback.payload = {}
                fallback.action = "window_focus"
                fallback.tool = "window_focus"
                fallback.payload["strategy"] = "switch_window"
                if fallback.ok:
                    fallback.payload["focus_backend_response"] = response
                    fallback.payload["focus_backend_response_detail"] = detail
                    fallback.payload["focus_backend_response_code"] = status
                else:
                    fallback.payload["backend_response"] = response
                    fallback.payload["backend_response_detail"] = detail
                    fallback.payload["backend_response_code"] = status
                return fallback
            return result

        result = self.switch_window(name, handle=handle, pid=pid)
        if result.payload is None:
            result.payload = {}
        result.action = "window_focus"
        result.tool = "window_focus"
        result.payload["strategy"] = "switch_window"
        return result

    def close_window(self, name: str, handle: int | None = None, pid: int | None = None) -> InputResult:
        def _capture_state() -> dict[str, Any]:
            windows = self._snapshot_windows(refresh=True)
            return {"active_window": windows[0] if windows else None, "windows": windows}

        def _matching_windows(snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
            if snapshot is None:
                return []
            windows = list(snapshot.get("windows", []) or [])
            matches: list[dict[str, Any]] = []
            normalized_name = self._normalize_window_name(name)
            for window in windows:
                if handle is not None and window.get("handle") == handle:
                    matches.append(window)
                    continue
                if pid is not None and window.get("pid") == pid:
                    matches.append(window)
                    continue
                if handle is None and pid is None and normalized_name and self._window_name_matches(window, name):
                    matches.append(window)
            return matches

        def _close_outcome(before: dict[str, Any] | None, after: dict[str, Any] | None, detail: str, exit_code: int | None, strategy: str, backend_response: Any, requested_close_path: str, matched_by: str, target_label: str) -> InputResult:
            before_matches = _matching_windows(before)
            after_matches = _matching_windows(after)
            before_target = before_matches[0] if before_matches else None
            after_target = after_matches[0] if after_matches else None
            before_present = bool(before_matches)
            after_present = bool(after_matches)
            count_decreased = len(before_matches) > len(after_matches)
            handle_gone = bool(handle is not None and before_present and not after_present)
            pid_decreased = bool(pid is not None and len(before_matches) > len(after_matches))
            verified = handle_gone or pid_decreased or count_decreased
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
                normalized_exit_code = normalized_exit_code if normalized_exit_code not in (None, 0) else 1
                normalized_detail = detail if detail.lower().startswith(("failed", "error")) else f"Close verification failed for {target_label}."

            return self._result(
                "window_close",
                normalized_detail,
                ok=ok,
                payload={
                    "name": name,
                    "target_window": target_label,
                    "matched_by": matched_by,
                    "close_strategy": strategy,
                    "requested_close_path": requested_close_path,
                    "backend_response": normalized_backend_response,
                    "exit_code": normalized_exit_code,
                    "before_window": before,
                    "after_window": after,
                    "before_match_count": len(before_matches),
                    "after_match_count": len(after_matches),
                    "post_close_verified": verified,
                    "outcome": outcome if ok or before_present else "capability_missing",
                    "target_handle": handle or (before_target or {}).get("handle"),
                    "target_pid": pid or (before_target or {}).get("pid"),
                    "verification_mode": (
                        "handle_removed"
                        if handle_gone
                        else "pid_count_decreased"
                        if pid_decreased
                        else "name_count_decreased"
                        if count_decreased
                        else "unverified"
                    ),
                    "before_target_window": before_target,
                    "after_target_window": after_target,
                },
                tool="window_close",
            )

        if self._backend is None:
            result = self._result(
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
                    "overlay_state": self._overlay_snapshot_payload(),
                },
                tool="window_close",
            )
            return result

        before = _capture_state()
        target_before, matched_by = self._resolve_target_window(name=name, handle=handle, pid=pid, refresh=False, prefer_active=True)
        target_label = (target_before or {}).get("name") or name
        target_handle = handle or (target_before or {}).get("handle")
        target_pid = pid or (target_before or {}).get("pid")

        if target_handle is not None and self._native_close_window(target_handle):
            time.sleep(0.15)
            after = _capture_state()
            result = _close_outcome(
                before,
                after,
                f"Posted WM_CLOSE to {target_label}.",
                0,
                "native.close_window",
                (f"Posted WM_CLOSE to {target_label}.", 0),
                "wm_close_native",
                matched_by,
                target_label,
            )
            if result.ok:
                if result.payload is not None:
                    result.payload["overlay_state"] = self._overlay_snapshot_payload()
                return result

        close_app = getattr(self._backend, "close_app", None)
        if callable(close_app):
            response = close_app(target_label)
            detail, exit_code = self._normalize_backend_response(response)
            time.sleep(0.15)
            after = _capture_state()
            result = _close_outcome(before, after, detail, exit_code, "backend.close_app", response, "wm_close", matched_by, target_label)
            if result.ok:
                if result.payload is not None:
                    result.payload["overlay_state"] = self._overlay_snapshot_payload()
                return result
            if target_handle is not None and self._native_close_window(target_handle):
                time.sleep(0.15)
                after = _capture_state()
                fallback = _close_outcome(
                    before,
                    after,
                    f"Posted WM_CLOSE to {target_label} after backend close_app fallback.",
                    0,
                    "native.close_window",
                    (f"Posted WM_CLOSE to {target_label} after backend close_app fallback.", 0),
                    "wm_close_native",
                    matched_by,
                    target_label,
                )
                if fallback.ok:
                    return fallback
            return result

        kill_process = getattr(self._backend, "kill_process", None)
        if callable(kill_process):
            response = kill_process(name=target_label, force=False)
            detail, exit_code = self._normalize_backend_response(response)
            after = _capture_state()
            result = _close_outcome(before, after, detail, exit_code, "backend.kill_process", response, "kill_process", matched_by, target_label)
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

    def _snapshot_window(
        self,
        name: str | None = None,
        refresh: bool = False,
        *,
        handle: int | None = None,
        pid: int | None = None,
        prefer_active: bool = False,
    ) -> dict[str, Any] | None:
        backend = self._backend
        if backend is None:
            return None

        try:
            if name is None and handle is None and pid is None:
                windows = self._snapshot_windows(refresh=refresh)
                return windows[0] if windows else None

            snapshot = self._find_window_snapshot(name=name, handle=handle, pid=pid, refresh=refresh, prefer_active=prefer_active)
            if snapshot is not None:
                return snapshot

            if refresh and name is not None and handle is None and pid is None:
                find_window = getattr(backend, "_find_window_by_name", None)
                if callable(find_window):
                    try:
                        target_window, _ = find_window(name, refresh_state=True)
                    except Exception:
                        target_window = None
                    snapshot = self._window_to_snapshot(target_window)
                    if snapshot is not None:
                        return snapshot
        except Exception:
            return None
        return None

    def _window_to_snapshot(self, window: Any) -> dict[str, Any] | None:
        if window is None:
            return None
        if isinstance(window, dict):
            return {
                "name": window.get("name") or window.get("window_title"),
                "status": getattr(window.get("status"), "name", None) or window.get("status"),
                "handle": window.get("handle"),
                "pid": window.get("pid") or window.get("process_id"),
                "window_title": window.get("window_title") or window.get("name"),
                "bounds": window.get("bounds"),
                "is_visible": window.get("is_visible"),
            }
        return {
            "name": getattr(window, "name", None) or getattr(window, "window_title", None),
            "status": getattr(getattr(window, "status", None), "name", None) or getattr(window, "status", None),
            "handle": getattr(window, "handle", None),
            "pid": getattr(window, "pid", None) or getattr(window, "process_id", None),
            "window_title": getattr(window, "window_title", None) or getattr(window, "name", None),
            "bounds": getattr(window, "bounds", None),
            "is_visible": getattr(window, "is_visible", None),
        }

    def _snapshot_windows(self, refresh: bool = False) -> list[dict[str, Any]]:
        backend = self._backend
        if backend is None:
            return []

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
            if state is None:
                return []

            windows: list[dict[str, Any]] = []
            seen: set[tuple[Any, Any, Any]] = set()
            candidates = [getattr(state, "active_window", None)] + list(getattr(state, "windows", []) or [])
            for candidate in candidates:
                snapshot = self._window_to_snapshot(candidate)
                if snapshot is None:
                    continue
                key = (snapshot.get("handle"), snapshot.get("pid"), snapshot.get("name"), snapshot.get("window_title"))
                if key in seen:
                    continue
                seen.add(key)
                windows.append(snapshot)
            self._remember_window_snapshots(windows)
            return windows
        except Exception:
            return []

    def _window_name_matches(self, snapshot: dict[str, Any] | None, name: str | None) -> bool:
        if snapshot is None or not name:
            return False
        target = self._normalize_window_name(name)
        return bool(target and target in self._window_name_candidates(snapshot))

    def _find_window_snapshot(
        self,
        *,
        name: str | None = None,
        handle: int | None = None,
        pid: int | None = None,
        refresh: bool = False,
        prefer_active: bool = False,
        include_history: bool = True,
    ) -> dict[str, Any] | None:
        windows = self._snapshot_windows(refresh=refresh)
        cached_windows = self._snapshot_windows_from_history() if include_history else []
        search_windows = list(windows)
        for snapshot in cached_windows:
            key = self._window_history_key(snapshot)
            if key is None:
                continue
            if any(self._window_history_key(existing) == key for existing in search_windows):
                continue
            search_windows.append(snapshot)
        if not search_windows:
            return None

        if handle is not None:
            for snapshot in search_windows:
                if snapshot.get("handle") == handle:
                    return snapshot
            return None

        if pid is not None:
            pid_matches = [snapshot for snapshot in search_windows if snapshot.get("pid") == pid]
            if pid_matches:
                if prefer_active and windows and windows[0].get("pid") == pid:
                    return windows[0]
                return pid_matches[0]
            if name is None:
                return None

        if name is None:
            return windows[0] if windows else search_windows[0]

        exact_matches = [snapshot for snapshot in search_windows if self._window_name_matches(snapshot, name)]
        if exact_matches:
            if prefer_active and windows and self._window_name_matches(windows[0], name):
                return windows[0]
            return exact_matches[0]

        return None

    @staticmethod
    def _normalize_backend_response(response: Any) -> tuple[str, int | None]:
        if isinstance(response, tuple) and response:
            detail = str(response[0])
            status = response[1] if len(response) > 1 and isinstance(response[1], int) else None
            return detail, status
        return str(response), None

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
        handle: int | None = None,
        pid: int | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> InputResult:
        original_before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
        if original_before is None:
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
        before_status = self._window_status(original_before)
        target_name = original_before.get("name") if original_before else name
        if self._backend is None:
            return self._result(
                "window_resize",
                f"resize:{name or 'active'}:{width}x{height}@{x},{y}",
                payload={**self._window_payload(target_window=target_name, before=original_before), "verified": False},
                tool="window_resize",
            )

        if hasattr(self._backend, "resize_app"):
            loc = (x, y) if x is not None and y is not None else None
            size = (width, height) if width is not None and height is not None else None
            reason = None
            target_handle = handle or original_before.get("handle")
            target_pid = pid or original_before.get("pid")
            attempted_restore = before_status in {"minimized", "maximized"}
            original_status = before_status
            original_rect_before = self._native_window_rect(target_handle)
            working_before = original_before
            if attempted_restore:
                reason = original_status
                restore_app = getattr(self._backend, "restore_app", None)
                restored = False
                if callable(restore_app):
                    try:
                        restore_app(name=target_name)
                    except Exception:
                        pass
                working_before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True) or working_before
                before_status = self._window_status(working_before)
                native_iconic = self._native_is_iconic(target_handle)
                native_zoomed = self._native_is_zoomed(target_handle)
                restored = before_status not in {"minimized", "maximized"} and native_iconic is not True and native_zoomed is not True
                if not restored and target_handle is not None and self._native_restore_window(target_handle):
                    time.sleep(0.08)
                    working_before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True) or working_before
                    before_status = self._window_status(working_before)
                    native_iconic = self._native_is_iconic(target_handle)
                    native_zoomed = self._native_is_zoomed(target_handle)
                    restored = before_status not in {"minimized", "maximized"} and native_iconic is not True and native_zoomed is not True
                if not restored:
                    after = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
                    return self._result(
                        "window_resize",
                        f"restore failed for {target_name}",
                        ok=False,
                        payload={
                            **self._window_payload(target_window=target_name, before=original_before, after=after),
                            "verified": False,
                            "reason": original_status,
                            "attempted_restore": attempted_restore,
                            "pre_resize_window": working_before,
                            "pre_resize_status": working_before.get("status") if working_before else None,
                            "original_native_rect_before": original_rect_before,
                            "native_is_iconic": native_iconic,
                            "native_is_zoomed": native_zoomed,
                            "error_kind": "restore_failed",
                            "error_message": f"Failed to restore window before resize: {target_name}",
                            "requested_size": {"width": width, "height": height},
                            "requested_position": {"x": x, "y": y},
                        },
                        tool="window_resize",
                    )
                reason = None
            try:
                response = self._backend.resize_app(name=target_name, size=size, loc=loc)
            except Exception as exc:
                after = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
                return self._result(
                    "window_resize",
                    f"resize failed:{exc}",
                    ok=False,
                    payload={
                        **self._window_payload(target_window=target_name, before=original_before, after=after),
                        "verified": False,
                        "reason": reason,
                        "attempted_restore": attempted_restore,
                        "pre_resize_window": working_before,
                        "pre_resize_status": working_before.get("status") if working_before else None,
                        "original_native_rect_before": original_rect_before,
                        "error_kind": "exception",
                        "error_message": str(exc),
                    },
                    tool="window_resize",
                )
            detail, status = self._normalize_backend_response(response)
            rect_before = self._native_window_rect(target_handle)
            move_fallback_used = False
            if status in (None, 0) and target_handle is not None and None not in {x, y, width, height}:
                if self._native_move_window(target_handle, x, y, width, height):
                    move_fallback_used = True
                    time.sleep(0.08)
            after = self._find_window_snapshot(handle=working_before.get("handle"), pid=working_before.get("pid"), name=name, refresh=True)
            if after is None:
                after = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True)
            after_status = self._window_status(after)
            rect_after = self._native_window_rect(target_handle)
            native_resized = bool(
                rect_after is not None
                and x is not None
                and y is not None
                and width is not None
                and height is not None
                and rect_after == {"left": x, "top": y, "right": x + width, "bottom": y + height}
            )
            snapshot_resized = bool(
                after
                and x is not None
                and y is not None
                and width is not None
                and height is not None
                and after.get("bounds") == [x, y, x + width, y + height]
            )
            backend_ack_active_target = bool(
                after
                and self._window_same_target(after, working_before)
                and (target_handle is None or rect_after is None or None in {x, y, width, height})
            )
            verified = bool(
                status in (None, 0)
                and after
                and after_status not in {"minimized", "maximized"}
                and (
                    native_resized
                    or snapshot_resized
                    or rect_after != rect_before
                    or backend_ack_active_target
                    or (width is None and height is None and x is None and y is None)
                )
            )
            ok_flag = verified
            if not ok_flag and after is None:
                detail = f"Resize verification failed for {target_name}."
            elif not ok_flag and after_status in {"maximized", "minimized"}:
                detail = f"{target_name} remained {after_status} after resize attempt."
            elif not ok_flag:
                detail = f"Resize verification failed for {target_name}."
            payload = {
                **self._window_payload(target_window=target_name, before=original_before, after=after),
                "verified": verified,
                "reason": reason,
                "attempted_restore": attempted_restore,
                "pre_resize_window": working_before,
                "pre_resize_status": working_before.get("status") if working_before else None,
                "original_native_rect_before": original_rect_before,
                "native_rect_before": rect_before,
                "native_rect_after": rect_after,
                "native_resized": native_resized,
                "snapshot_resized": snapshot_resized,
                "backend_ack_active_target": backend_ack_active_target,
                "move_fallback_used": move_fallback_used,
                "requested_size": {"width": width, "height": height},
                "requested_position": {"x": x, "y": y},
                "backend_response": response,
                "backend_response_detail": detail,
                "backend_response_code": status,
            }
            return self._result("window_resize", detail, ok=ok_flag, payload=payload, tool="window_resize")

        raise ExecutorError("Backend does not expose resize_app().")

    def minimize_window(self, name: str | None = None, handle: int | None = None, pid: int | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True) or {"name": name, "status": None, "handle": handle, "pid": pid}
        if self._backend is None:
            return self._result(
                "window_minimize",
                f"minimize:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_minimize",
            )
        if hasattr(self._backend, "minimize_app"):
            target_handle = handle or (before.get("handle") if before else None)
            target_pid = pid or (before.get("pid") if before else None)
            response = self._backend.minimize_app(name=before.get("name") if before else name)
            detail, status = self._normalize_backend_response(response)
            observations = self._poll_window_observations(name=name, handle=target_handle, pid=target_pid, attempts=6, delay=0.12)
            after = observations[-1]["target"] if observations else None
            active_after = observations[-1]["active"] if observations else None
            visible_after = observations[-1]["visible"] if observations else []
            target_handle_present_after = bool(target_handle is not None and any(window.get("handle") == target_handle for window in visible_after))
            verification_mode = "unverified"
            verified = False
            native_iconic = self._native_is_iconic(target_handle)
            if status in (None, 0):
                for observation in observations:
                    observed_target = observation["target"]
                    observed_active = observation["active"]
                    observed_visible = observation["visible"]
                    target_handle_visible = bool(target_handle is not None and any(window.get("handle") == target_handle for window in observed_visible))
                    if self._window_is_minimized(observed_target):
                        after = observed_target
                        active_after = observed_active
                        visible_after = observed_visible
                        target_handle_present_after = target_handle_visible
                        verified = True
                        verification_mode = "status_minimized"
                        break
                    if observed_target is not None and observed_target.get("is_visible") is False:
                        after = observed_target
                        active_after = observed_active
                        visible_after = observed_visible
                        target_handle_present_after = target_handle_visible
                        verified = True
                        verification_mode = "visibility_hidden_after_minimize"
                        break
                    if target_handle is not None and not target_handle_visible and (observed_active is None or observed_active.get("handle") != target_handle):
                        after = observed_target
                        active_after = observed_active
                        visible_after = observed_visible
                        target_handle_present_after = target_handle_visible
                        verified = True
                        verification_mode = "handle_hidden_after_minimize"
                        break
            if not verified and status in (None, 0) and target_handle is not None and self._native_show_window(target_handle, 6):
                time.sleep(0.12)
                observations = self._poll_window_observations(name=name, handle=target_handle, pid=target_pid, attempts=6, delay=0.12)
                after = observations[-1]["target"] if observations else None
                active_after = observations[-1]["active"] if observations else None
                visible_after = observations[-1]["visible"] if observations else []
                target_handle_present_after = bool(target_handle is not None and any(window.get("handle") == target_handle for window in visible_after))
                native_iconic = self._native_is_iconic(target_handle)
                if native_iconic is True:
                    verified = True
                    verification_mode = "native_iconic"
            payload = {
                **self._window_payload(target_window=before.get("name") if before else name, before=before, after=after),
                "verified": verified,
                "verification_mode": verification_mode,
                "target_instance_handle": target_handle,
                "target_instance_pid": target_pid,
                "target_handle_present_after": target_handle_present_after,
                "target_window_after_matches_target": self._window_same_target(after, before),
                "active_window_after_matches_target": self._window_same_target(active_after, before),
                "active_window_after": active_after,
                "native_is_iconic": native_iconic,
                "backend_response": response,
                "backend_response_detail": detail,
                "backend_response_code": status,
            }
            detail = detail if verified else f"Minimize verification failed for {before.get('name') if before else (name or 'active')}."
            return self._result("window_minimize", detail, ok=verified, payload=payload, tool="window_minimize")
        raise ExecutorError("Backend does not expose minimize_app().")

    def maximize_window(self, name: str | None = None, handle: int | None = None, pid: int | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True) or {"name": name, "status": None, "handle": handle, "pid": pid}
        if self._backend is None:
            return self._result(
                "window_maximize",
                f"maximize:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_maximize",
            )
        if hasattr(self._backend, "maximize_app"):
            target_handle = handle or (before.get("handle") if before else None)
            target_pid = pid or (before.get("pid") if before else None)
            response = self._backend.maximize_app(name=before.get("name") if before else name)
            detail, status = self._normalize_backend_response(response)
            observations = self._poll_window_observations(name=name, handle=target_handle, pid=target_pid, prefer_active=True, attempts=6, delay=0.12)
            after = observations[-1]["target"] if observations else None
            verification_mode = "unverified"
            verified = False
            before_area = self._window_bounds_area(before)
            native_zoomed = self._native_is_zoomed(target_handle)
            if status in (None, 0):
                for observation in observations:
                    observed_target = observation["target"]
                    observed_active = observation["active"]
                    after_area = self._window_bounds_area(observed_target)
                    if self._window_is_maximized(observed_target):
                        after = observed_target
                        verified = True
                        verification_mode = "status_maximized"
                        break
                    if self._window_is_maximized(before) and self._window_same_target(observed_target, before):
                        after = observed_target
                        verified = True
                        verification_mode = "already_maximized"
                        break
                    if before_area and after_area and after_area > int(before_area * 1.15):
                        after = observed_target
                        verified = True
                        verification_mode = "bounds_expanded"
                        break
            if not verified and status in (None, 0) and target_handle is not None and self._native_show_window(target_handle, 3):
                time.sleep(0.12)
                observations = self._poll_window_observations(name=name, handle=target_handle, pid=target_pid, prefer_active=True, attempts=6, delay=0.12)
                after = observations[-1]["target"] if observations else None
                native_zoomed = self._native_is_zoomed(target_handle)
                if native_zoomed is True:
                    verified = True
                    verification_mode = "native_zoomed"
            payload = {
                **self._window_payload(target_window=before.get("name") if before else name, before=before, after=after),
                "verified": verified,
                "verification_mode": verification_mode,
                "native_is_zoomed": native_zoomed,
                "backend_response": response,
                "backend_response_detail": detail,
                "backend_response_code": status,
            }
            detail = detail if verified else f"Maximize verification failed for {before.get('name') if before else (name or 'active')}."
            return self._result("window_maximize", detail, ok=verified, payload=payload, tool="window_maximize")
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

    def restore_window(self, name: str | None = None, handle: int | None = None, pid: int | None = None) -> InputResult:
        before = self._snapshot_window(name, refresh=True, handle=handle, pid=pid, prefer_active=True) or {"name": name, "status": None, "handle": handle, "pid": pid}
        if self._backend is None:
            return self._result(
                "window_restore",
                f"restore:{name or 'active'}",
                payload={**self._window_payload(target_window=before.get("name") if before else name, before=before), "verified": False},
                tool="window_restore",
            )
        if hasattr(self._backend, "restore_app"):
            target_handle = handle or before.get("handle")
            target_pid = pid or before.get("pid")
            response: Any
            detail: str
            status: int | None
            strategy = "restore_app"
            if target_handle is not None and self._native_restore_window(target_handle):
                detail = f"Restored {before.get('name') if before else (name or target_handle)} window via native handle fallback."
                status = 0
                response = (detail, 0)
                strategy = "native_handle"
            else:
                response = self._backend.restore_app(name=before.get("name") if before else name)
                detail, status = self._normalize_backend_response(response)
            observations = self._poll_window_observations(name=name, handle=target_handle, pid=target_pid, prefer_active=True, attempts=6, delay=0.12)
            after = observations[-1]["target"] if observations else None
            active_after = observations[-1]["active"] if observations else None
            native_iconic = self._native_is_iconic(target_handle)
            native_zoomed = self._native_is_zoomed(target_handle)
            target_visible_after = bool(
                target_handle is not None
                and any(
                    window.get("handle") == target_handle
                    for observation in observations
                    for window in observation.get("visible", [])
                )
            )
            verification_mode = "unverified"
            verified = bool(
                status in (None, 0)
                and after
                and (
                    (
                        not self._window_is_minimized(after)
                        and not self._window_is_maximized(after)
                        and (
                            active_after is None
                            or self._window_same_target(active_after, after)
                            or self._window_name_matches(active_after, name)
                        )
                    )
                    or (
                        strategy == "native_handle"
                        and native_iconic is not True
                        and (
                            self._window_same_target(active_after, after)
                            or (target_handle is not None and active_after is not None and active_after.get("handle") == target_handle)
                            or target_visible_after
                        )
                    )
                )
            )
            if verified:
                if strategy == "native_handle" and native_iconic is not True and native_zoomed is True:
                    verification_mode = "native_zoomed_visible"
                elif strategy == "native_handle" and native_iconic is not True and target_visible_after:
                    verification_mode = "native_handle_visible"
                else:
                    verification_mode = "status_normal"
            payload = {
                **self._window_payload(target_window=before.get("name") if before else name, before=before, after=after),
                "verified": verified,
                "active_window_after": active_after,
                "verification_mode": verification_mode,
                "native_is_iconic": native_iconic,
                "native_is_zoomed": native_zoomed,
                "target_visible_after": target_visible_after,
                "backend_response": response,
                "backend_response_detail": detail,
                "backend_response_code": status,
                "strategy": strategy,
            }
            detail = detail if verified else f"Restore verification failed for {before.get('name') if before else (name or 'active')}."
            return self._result("window_restore", detail, ok=verified, payload=payload, tool="window_restore")
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
