from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .pathgen import PathGenerator


class MotionPhase(str, Enum):
    PLANNED = "planned"
    ANIMATING = "animating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    x: int = 0
    y: int = 0
    phase: MotionPhase = MotionPhase.PLANNED
    active_action: MotionAction | None = None
    trail: list[MotionPoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
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

    def __init__(self, *, default_duration_ms: int = 180, cursor_state: VirtualCursorState | None = None, seed: int = 7, debug_show_points: bool = False, debug_show_target: bool = False) -> None:
        self.default_duration_ms = default_duration_ms
        self.cursor_state = cursor_state or VirtualCursorState()
        self._pathgen = PathGenerator(seed=seed)
        self.debug_show_points = debug_show_points
        self.debug_show_target = debug_show_target

    def build_path(self, action: MotionAction, steps: int = 16) -> list[MotionPoint]:
        return self._pathgen.build(action, steps=steps)

    def plan(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, metadata: dict[str, Any] | None = None, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, action_id: str | None = None) -> MotionAction:
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
        event = MotionEvent(action_id=action.action_id or "planned", kind=action.kind, phase=MotionPhase.PLANNED, timestamp_ms=0, detail="motion planned", metadata={"steps": len(path), "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target})
        metadata = {"steps": len(path), "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target}
        if self.debug_show_points:
            metadata["points"] = [{"x": point.x, "y": point.y, "t": point.t} for point in path]
        if self.debug_show_target:
            metadata["target"] = {"x": action.end.x, "y": action.end.y}
        return MotionResult(ok=True, phase=MotionPhase.PLANNED, action=action, path=path, detail="motion planned", metadata=metadata, event=event)

    def execute(self, action: MotionAction, steps: int = 16) -> MotionResult:
        self.cursor_state.phase = MotionPhase.ANIMATING
        self.cursor_state.active_action = action
        path = self.build_path(action, steps=steps)
        if not path:
            self.cursor_state.phase = MotionPhase.FAILED
            self.cursor_state.metadata = {"error": "empty_path", "kind": action.kind}
            raise MotionExecutionError("Motion execution produced an empty path.")
        if action.cancelled:
            self.cursor_state.phase = MotionPhase.CANCELLED
            event = MotionEvent(action_id=action.action_id or "cancelled", kind=action.kind, phase=MotionPhase.CANCELLED, timestamp_ms=0, detail="motion cancelled")
            return MotionResult(ok=False, phase=MotionPhase.CANCELLED, action=action, path=path, detail="motion cancelled", metadata={"steps": len(path), "cancelled": True}, event=event)
        self.cursor_state.phase = MotionPhase.EXECUTING
        self.cursor_state.phase = MotionPhase.VERIFYING
        self.cursor_state.trail = list(path)
        self.cursor_state.x = action.end.x
        self.cursor_state.y = action.end.y
        self.cursor_state.phase = MotionPhase.VERIFIED
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
        }
        metadata = {"steps": len(path), "verified": True, "debug_show_points": self.debug_show_points, "debug_show_target": self.debug_show_target}
        if self.debug_show_points:
            metadata["points"] = [{"x": point.x, "y": point.y, "t": point.t} for point in path]
        if self.debug_show_target:
            metadata["target"] = {"x": action.end.x, "y": action.end.y}
        event = MotionEvent(action_id=action.action_id or "executed", kind=action.kind, phase=MotionPhase.VERIFIED, timestamp_ms=0, detail="motion executed", metadata=metadata)
        return MotionResult(ok=True, phase=MotionPhase.VERIFIED, action=action, path=path, detail="motion executed", metadata=metadata, event=event)

    def run(self, action: MotionAction, steps: int = 16) -> MotionResult:
        return self.execute(action, steps=steps)

    def transition_allowed(self, from_phase: MotionPhase, to_phase: MotionPhase) -> bool:
        order = {phase: index for index, phase in enumerate(FROZEN_PHASE_FLOW)}
        return order.get(to_phase, -1) >= order.get(from_phase, -1)
