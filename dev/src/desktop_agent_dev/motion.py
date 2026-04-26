from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .pathgen import PathGenerator


class MotionPhase(str, Enum):
    PLANNED = "planned"
    ANIMATING = "animating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


DEFAULT_CLICK_PREMOVE_MS = 280
DEFAULT_LONG_MOVE_MS = 640
DEFAULT_DRAG_MS = 1100
DEFAULT_OBSERVE_PAUSE_MS = 220
DEFAULT_CLICK_RIPPLE_MS = 150
DEFAULT_CLICK_RIPPLE_RADIUS = 18
DEFAULT_TRAIL_TAIL_MS = 140

FROZEN_ACTION_TYPES = ("move", "click", "drag", "scroll", "focus", "type")
FROZEN_PHASE_FLOW = (
    MotionPhase.PLANNED,
    MotionPhase.ANIMATING,
    MotionPhase.EXECUTING,
    MotionPhase.VERIFYING,
    MotionPhase.VERIFIED,
    MotionPhase.FAILED,
    MotionPhase.CANCELLED,
)


@dataclass(slots=True)
class MotionEvent:
    action_id: str
    kind: str
    phase: MotionPhase
    timestamp_ms: int
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_data(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "phase": self.phase.value,
            "timestamp_ms": self.timestamp_ms,
            "detail": self.detail,
            "metadata": dict(self.metadata),
        }


class MotionExecutionError(RuntimeError):
    pass


@dataclass(slots=True)
class MotionPoint:
    x: int
    y: int
    t: float | None = None


@dataclass(slots=True)
class MotionAction:
    kind: str
    start: MotionPoint
    end: MotionPoint
    duration_ms: int = 180
    easing: str = "ease_out_quad"
    metadata: dict[str, Any] = field(default_factory=dict)
    hover_ms: int = 0
    jitter_px: int = 0
    accel: float = 1.0
    decel: float = 1.0
    action_id: str | None = None
    cancelled: bool = False


@dataclass(slots=True)
class MotionResult:
    ok: bool
    phase: MotionPhase
    action: MotionAction
    path: list[MotionPoint] = field(default_factory=list)
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    event: MotionEvent | None = None

    def as_data(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "phase": self.phase.value,
            "action": {
                "kind": self.action.kind,
                "start": {"x": self.action.start.x, "y": self.action.start.y},
                "end": {"x": self.action.end.x, "y": self.action.end.y},
                "duration_ms": self.action.duration_ms,
                "easing": self.action.easing,
                "metadata": dict(self.action.metadata),
                "hover_ms": self.action.hover_ms,
                "jitter_px": self.action.jitter_px,
                "accel": self.action.accel,
                "decel": self.action.decel,
                "action_id": self.action.action_id,
                "cancelled": self.action.cancelled,
            },
            "path": [{"x": point.x, "y": point.y, "t": point.t} for point in self.path],
            "detail": self.detail,
            "metadata": dict(self.metadata),
            "event": None if self.event is None else self.event.as_data(),
        }


@dataclass(slots=True)
class VirtualCursorState:
    visible: bool = True
    x: int = 0
    y: int = 0
    pressed: bool = False
    target_x: int | None = None
    target_y: int | None = None
    velocity: float = 0.0
    state: str = "idle"
    phase: MotionPhase = MotionPhase.PLANNED
    active_action: MotionAction | None = None
    trail: list[MotionPoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "visible": self.visible,
            "x": self.x,
            "y": self.y,
            "pressed": self.pressed,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "velocity": self.velocity,
            "state": self.state,
            "phase": self.phase.value,
            "active_action": None if self.active_action is None else {
                "kind": self.active_action.kind,
                "start": {"x": self.active_action.start.x, "y": self.active_action.start.y},
                "end": {"x": self.active_action.end.x, "y": self.active_action.end.y},
                "duration_ms": self.active_action.duration_ms,
                "easing": self.active_action.easing,
                "metadata": dict(self.active_action.metadata),
            },
            "trail": [{"x": point.x, "y": point.y, "t": point.t} for point in self.trail],
            "metadata": dict(self.metadata),
        }


class MotionScheduler:
    """Motion scheduler with virtual cursor planning and execution state tracking."""

    def __init__(self, *, default_duration_ms: int = DEFAULT_CLICK_PREMOVE_MS, cursor_state: VirtualCursorState | None = None, seed: int = 7, debug_show_points: bool = False, debug_show_target: bool = False) -> None:
        self.default_duration_ms = default_duration_ms
        self.cursor_state = cursor_state or VirtualCursorState()
        self._pathgen = PathGenerator(seed=seed)
        self.debug_show_points = debug_show_points
        self.debug_show_target = debug_show_target

    def build_path(self, action: MotionAction, steps: int = 16) -> list[MotionPoint]:
        return self._pathgen.build(action, steps=steps)

    def _cancel_result(self, action: MotionAction, path: list[MotionPoint], *, reason: str | None = None) -> MotionResult:
        cancelled_event = self._transition_cursor_state(action, MotionPhase.CANCELLED)
        metadata = {"steps": len(path), "cancelled": True, "cancel_reason": reason, "phase_history": list(self.cursor_state.metadata.get("phase_history", []))}
        return MotionResult(ok=False, phase=MotionPhase.CANCELLED, action=action, path=path, detail="motion cancelled" if reason is None else f"motion cancelled:{reason}", metadata=metadata, event=cancelled_event)

    def _timestamp_ms(self, action: MotionAction, step_index: int, step_count: int) -> int:
        if step_count <= 1:
            return 0
        ratio = step_index / max(step_count - 1, 1)
        return round(action.duration_ms * ratio)

    def _transition_cursor_state(self, action: MotionAction, phase: MotionPhase) -> MotionEvent:
        state_map = {
            MotionPhase.PLANNED: "planning",
            MotionPhase.ANIMATING: "animating",
            MotionPhase.EXECUTING: "executing",
            MotionPhase.VERIFYING: "verifying",
            MotionPhase.VERIFIED: "idle",
            MotionPhase.FAILED: "failed",
            MotionPhase.CANCELLED: "cancelled",
        }
        self.cursor_state.visible = True
        self.cursor_state.phase = phase
        self.cursor_state.state = state_map[phase]
        self.cursor_state.active_action = action
        self.cursor_state.target_x = action.end.x
        self.cursor_state.target_y = action.end.y
        if phase in {MotionPhase.CANCELLED, MotionPhase.FAILED, MotionPhase.VERIFIED}:
            self.cursor_state.pressed = False
        elif phase is MotionPhase.EXECUTING:
            self.cursor_state.pressed = action.kind == "drag"
        event = MotionEvent(
            action_id=action.action_id or action.kind,
            kind=action.kind,
            phase=phase,
            timestamp_ms=0,
            detail=f"motion {phase.value}",
            metadata={"target": {"x": action.end.x, "y": action.end.y}},
        )
        history = list(self.cursor_state.metadata.get("phase_history", []))
        history.append(phase.value)
        self.cursor_state.metadata["phase_history"] = history[-16:]
        self.cursor_state.metadata["last_phase"] = phase.value
        return event

    def _step_cursor_state(self, action: MotionAction, point: MotionPoint, previous: MotionPoint | None, step_index: int, step_count: int) -> None:
        self.cursor_state.x = point.x
        self.cursor_state.y = point.y
        self.cursor_state.trail.append(point)
        if len(self.cursor_state.trail) > 128:
            self.cursor_state.trail = self.cursor_state.trail[-128:]
        if previous is None:
            velocity = 0.0
        else:
            dx = point.x - previous.x
            dy = point.y - previous.y
            velocity = (dx * dx + dy * dy) ** 0.5
        self.cursor_state.velocity = velocity
        self.cursor_state.metadata.update(
            {
                "step_index": step_index,
                "step_count": step_count,
                "progress": round(step_index / max(step_count - 1, 1), 4) if step_count > 1 else 1.0,
                "timestamp_ms": self._timestamp_ms(action, step_index, step_count),
                "last_point": {"x": point.x, "y": point.y, "t": point.t},
                "velocity": velocity,
            }
        )

    def plan(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, metadata: dict[str, Any] | None = None, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, action_id: str | None = None) -> MotionAction:
        if duration_ms is None:
            duration_ms = DEFAULT_LONG_MOVE_MS if kind == "move" else DEFAULT_DRAG_MS if kind == "drag" else DEFAULT_CLICK_PREMOVE_MS
        metadata = metadata or {}
        return MotionAction(
            kind=kind,
            start=MotionPoint(*start),
            end=MotionPoint(*end),
            duration_ms=duration_ms or self.default_duration_ms,
            metadata=metadata,
            hover_ms=hover_ms,
            jitter_px=jitter_px,
            accel=accel,
            decel=decel,
            action_id=action_id,
        )

    def plan_result(self, action: MotionAction, steps: int = 16) -> MotionResult:
        path = self.build_path(action, steps=steps)
        self.cursor_state.visible = True
        self.cursor_state.target_x = action.end.x
        self.cursor_state.target_y = action.end.y
        self.cursor_state.state = "planning"
        self.cursor_state.phase = MotionPhase.PLANNED
        self.cursor_state.active_action = action
        event = MotionEvent(action_id=action.action_id or "planned", kind=action.kind, phase=MotionPhase.PLANNED, timestamp_ms=0, detail="motion planned", metadata={"steps": len(path), "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target})
        metadata = {"steps": len(path), "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target}
        if self.debug_show_points:
            metadata["points"] = [{"x": point.x, "y": point.y, "t": point.t} for point in path]
        if self.debug_show_target:
            metadata["target"] = {"x": action.end.x, "y": action.end.y}
        return MotionResult(ok=True, phase=MotionPhase.PLANNED, action=action, path=path, detail="motion planned", metadata=metadata, event=event)

    def execute(self, action: MotionAction, steps: int = 16, on_update: Callable[[dict[str, Any]], None] | None = None, should_cancel: Callable[[MotionPhase, MotionPoint | None], str | None] | None = None) -> MotionResult:
        path = self.build_path(action, steps=steps)
        planned_event = self._transition_cursor_state(action, MotionPhase.PLANNED)
        if on_update is not None:
            on_update({"type": "phase", "event": planned_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
        if not path:
            failed_event = self._transition_cursor_state(action, MotionPhase.FAILED)
            self.cursor_state.metadata = {"error": "empty_path", "kind": action.kind}
            if on_update is not None:
                on_update({"type": "phase", "event": failed_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
            raise MotionExecutionError("Motion execution produced an empty path.")
        if action.cancelled:
            cancelled = self._cancel_result(action, path)
            if on_update is not None and cancelled.event is not None:
                on_update({"type": "phase", "event": cancelled.event.as_data(), "cursor_state": self.cursor_state.snapshot()})
            return cancelled
        if should_cancel is not None:
            cancel_reason = should_cancel(MotionPhase.ANIMATING, None)
            if cancel_reason is not None:
                cancelled = self._cancel_result(action, path, reason=cancel_reason)
                if on_update is not None and cancelled.event is not None:
                    on_update({"type": "phase", "event": cancelled.event.as_data(), "cursor_state": self.cursor_state.snapshot()})
                return cancelled
        animating_event = self._transition_cursor_state(action, MotionPhase.ANIMATING)
        if on_update is not None:
            on_update({"type": "phase", "event": animating_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
        self.cursor_state.trail = []
        previous: MotionPoint | None = None
        step_count = len(path)
        for index, point in enumerate(path):
            if should_cancel is not None:
                cancel_reason = should_cancel(MotionPhase.ANIMATING, point)
                if cancel_reason is not None:
                    cancelled = self._cancel_result(action, path[: index + 1], reason=cancel_reason)
                    if on_update is not None and cancelled.event is not None:
                        on_update({"type": "phase", "event": cancelled.event.as_data(), "cursor_state": self.cursor_state.snapshot()})
                    return cancelled
            self._step_cursor_state(action, point, previous, index, step_count)
            if on_update is not None:
                on_update(
                    {
                        "type": "point",
                        "point": {"x": point.x, "y": point.y, "t": point.t},
                        "step_index": index,
                        "step_count": step_count,
                        "cursor_state": self.cursor_state.snapshot(),
                    }
                )
            previous = point
        executing_event = self._transition_cursor_state(action, MotionPhase.EXECUTING)
        if on_update is not None:
            on_update({"type": "phase", "event": executing_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
        if should_cancel is not None:
            cancel_reason = should_cancel(MotionPhase.EXECUTING, previous)
            if cancel_reason is not None:
                cancelled = self._cancel_result(action, path, reason=cancel_reason)
                if on_update is not None and cancelled.event is not None:
                    on_update({"type": "phase", "event": cancelled.event.as_data(), "cursor_state": self.cursor_state.snapshot()})
                return cancelled
        verifying_event = self._transition_cursor_state(action, MotionPhase.VERIFYING)
        if on_update is not None:
            on_update({"type": "phase", "event": verifying_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
        if should_cancel is not None:
            cancel_reason = should_cancel(MotionPhase.VERIFYING, previous)
            if cancel_reason is not None:
                cancelled = self._cancel_result(action, path, reason=cancel_reason)
                if on_update is not None and cancelled.event is not None:
                    on_update({"type": "phase", "event": cancelled.event.as_data(), "cursor_state": self.cursor_state.snapshot()})
                return cancelled
        verified_event = self._transition_cursor_state(action, MotionPhase.VERIFIED)
        if on_update is not None:
            on_update({"type": "phase", "event": verified_event.as_data(), "cursor_state": self.cursor_state.snapshot()})
        self.cursor_state.metadata = {
            "steps": len(path),
            "kind": action.kind,
            "duration_ms": action.duration_ms,
            "hover_ms": action.hover_ms,
            "jitter_px": action.jitter_px,
            "accel": action.accel,
            "decel": action.decel,
            "last_target": {"x": action.end.x, "y": action.end.y},
            "last_status": MotionPhase.VERIFIED.value,
            "phase_history": list(self.cursor_state.metadata.get("phase_history", [])),
        }
        metadata = {"steps": len(path), "verified": True, "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target, "phase_history": list(self.cursor_state.metadata.get("phase_history", []))}
        if self.debug_show_points:
            metadata["points"] = [{"x": point.x, "y": point.y, "t": point.t} for point in path]
        if self.debug_show_target:
            metadata["target"] = {"x": action.end.x, "y": action.end.y}
        return MotionResult(ok=True, phase=MotionPhase.VERIFIED, action=action, path=path, detail="motion executed", metadata=metadata, event=verified_event)

    def run(self, action: MotionAction, steps: int = 16) -> MotionResult:
        return self.execute(action, steps=steps)

    def transition_allowed(self, from_phase: MotionPhase, to_phase: MotionPhase) -> bool:
        order = {phase: index for index, phase in enumerate(FROZEN_PHASE_FLOW)}
        return order.get(to_phase, -1) >= order.get(from_phase, -1)
