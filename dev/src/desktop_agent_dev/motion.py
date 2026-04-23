from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import cos, pi, sin
from random import Random
from typing import Any


class MotionPhase(str, Enum):
    PLANNED = "planned"
    ANIMATING = "animating"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


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


@dataclass(slots=True)
class MotionResult:
    ok: bool
    phase: MotionPhase
    action: MotionAction
    path: list[MotionPoint] = field(default_factory=list)
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


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
    """First-pass motion scheduler with virtual mouse state tracking."""

    def __init__(self, *, default_duration_ms: int = 180, cursor_state: VirtualCursorState | None = None, seed: int = 7) -> None:
        self.default_duration_ms = default_duration_ms
        self.cursor_state = cursor_state or VirtualCursorState()
        self._rng = Random(seed)

    def _ease_value(self, ratio: float, accel: float, decel: float, easing: str) -> float:
        ratio = max(0.0, min(1.0, ratio))
        if easing == "linear":
            return ratio
        if easing == "ease_in_out":
            if ratio < 0.5:
                return 0.5 * (2 * ratio) ** max(accel, 0.1)
            return 1 - 0.5 * (2 * (1 - ratio)) ** max(decel, 0.1)
        if ratio < 0.5:
            return 0.5 * (2 * ratio) ** max(accel, 0.1)
        return 1 - 0.5 * (2 * (1 - ratio)) ** max(decel, 0.1)

    def _apply_jitter(self, x: int, y: int, jitter_px: int, phase: float) -> tuple[int, int]:
        if jitter_px <= 0:
            return x, y
        wave = sin(phase * pi) * jitter_px
        wobble = cos(phase * pi * 2) * (jitter_px * 0.35)
        offset_x = round(wave * 0.6 + wobble)
        offset_y = round(wave * 0.4 - wobble)
        if phase < 0.2 or phase > 0.8:
            offset_x += self._rng.randint(-1, 1)
            offset_y += self._rng.randint(-1, 1)
        return x + offset_x, y + offset_y

    def _smooth_segment(self, start: MotionPoint, end: MotionPoint, steps: int, accel: float, decel: float, jitter_px: int, easing: str, phase_offset: float = 0.0) -> list[MotionPoint]:
        points: list[MotionPoint] = []
        if steps < 2:
            steps = 2
        for index in range(steps):
            ratio = index / (steps - 1)
            eased = self._ease_value(ratio, accel, decel, easing)
            x = round(start.x + (end.x - start.x) * eased)
            y = round(start.y + (end.y - start.y) * eased)
            x, y = self._apply_jitter(x, y, jitter_px, min(1.0, max(0.0, ratio + phase_offset)))
            points.append(MotionPoint(x=x, y=y, t=ratio))
        return points

    def _bezier_midpoint(self, start: MotionPoint, end: MotionPoint, curvature: float = 0.18) -> MotionPoint:
        dx = end.x - start.x
        dy = end.y - start.y
        control_x = round((start.x + end.x) / 2 - dy * curvature)
        control_y = round((start.y + end.y) / 2 + dx * curvature)
        return MotionPoint(x=control_x, y=control_y, t=0.5)

    def build_path(self, action: MotionAction, steps: int = 16) -> list[MotionPoint]:
        if steps < 2:
            steps = 2
        path: list[MotionPoint] = []
        if action.hover_ms > 0:
            hover_steps = max(2, min(6, steps // 4))
            hover_end = MotionPoint(
                x=action.start.x + self._rng.randint(-1, 1),
                y=action.start.y + self._rng.randint(-1, 1),
                t=0.0,
            )
            path.extend(self._smooth_segment(action.start, hover_end, hover_steps, 0.9, 1.1, max(0, action.jitter_px - 1), "ease_in_out"))
        if action.kind == "drag":
            mid = self._bezier_midpoint(action.start, action.end, curvature=0.14)
            first_half = self._smooth_segment(action.start, mid, max(2, steps // 2), action.accel, action.decel, action.jitter_px, action.easing)
            second_half = self._smooth_segment(mid, action.end, max(2, steps - len(first_half) + 1), action.accel * 0.9, action.decel * 1.1, max(0, action.jitter_px - 1), action.easing, phase_offset=0.5)
            path.extend(first_half[:-1])
            path.extend(second_half)
        elif action.kind == "move":
            bend = self._bezier_midpoint(action.start, action.end, curvature=0.22)
            arc_first = self._smooth_segment(action.start, bend, max(2, steps // 2), action.accel, action.decel, action.jitter_px, "ease_in_out")
            arc_second = self._smooth_segment(bend, action.end, max(2, steps - len(arc_first) + 1), action.accel, action.decel, action.jitter_px, "ease_in_out", phase_offset=0.4)
            path.extend(arc_first[:-1])
            path.extend(arc_second)
        else:
            path.extend(self._smooth_segment(action.start, action.end, steps, action.accel, action.decel, action.jitter_px, action.easing))
        if action.kind == "click":
            path.append(MotionPoint(x=action.end.x, y=action.end.y, t=1.0))
        return path

    def plan(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, metadata: dict[str, Any] | None = None, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0) -> MotionAction:
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
        )

    def run(self, action: MotionAction, steps: int = 16) -> MotionResult:
        self.cursor_state.phase = MotionPhase.ANIMATING
        self.cursor_state.active_action = action
        path = self.build_path(action, steps=steps)
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
        }
        return MotionResult(ok=True, phase=MotionPhase.VERIFIED, action=action, path=path, detail="motion planned", metadata={"steps": len(path)})
