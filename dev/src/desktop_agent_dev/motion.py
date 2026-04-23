from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
    metadata: dict[str, Any] = field(default_factory=dict)


class MotionScheduler:
    """Minimal first-pass motion scheduler skeleton."""

    def __init__(self, *, default_duration_ms: int = 180) -> None:
        self.default_duration_ms = default_duration_ms

    def build_path(self, action: MotionAction, steps: int = 16) -> list[MotionPoint]:
        if steps < 2:
            steps = 2
        path: list[MotionPoint] = []
        for index in range(steps):
            ratio = index / (steps - 1)
            x = round(action.start.x + (action.end.x - action.start.x) * ratio)
            y = round(action.start.y + (action.end.y - action.start.y) * ratio)
            path.append(MotionPoint(x=x, y=y, t=ratio))
        return path

    def plan(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, metadata: dict[str, Any] | None = None) -> MotionAction:
        return MotionAction(
            kind=kind,
            start=MotionPoint(*start),
            end=MotionPoint(*end),
            duration_ms=duration_ms or self.default_duration_ms,
            metadata=metadata or {},
        )

    def run(self, action: MotionAction, steps: int = 16) -> MotionResult:
        path = self.build_path(action, steps=steps)
        return MotionResult(ok=True, phase=MotionPhase.VERIFIED, action=action, path=path, detail="motion planned", metadata={"steps": len(path)})
