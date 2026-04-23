from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .motion import MotionAction, MotionScheduler, MotionResult
from .overlay import OverlayRenderer


@dataclass(slots=True)
class OrchestrationResult:
    ok: bool
    motion: MotionResult | None = None
    overlay_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class DesktopOrchestrator:
    """Coordinates motion planning and dev overlay state for the first rollout."""

    def __init__(self, *, motion_scheduler: MotionScheduler | None = None, overlay_renderer: OverlayRenderer | None = None) -> None:
        self.motion_scheduler = motion_scheduler or MotionScheduler()
        self.overlay_renderer = overlay_renderer or OverlayRenderer()

    def preview_motion(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, steps: int = 16) -> OrchestrationResult:
        action = self.motion_scheduler.plan(kind=kind, start=start, end=end, duration_ms=duration_ms)
        self.overlay_renderer.update_cursor(start[0], start[1])
        motion = self.motion_scheduler.run(action, steps=steps)
        self.overlay_renderer.update_cursor(end[0], end[1])
        return OrchestrationResult(ok=motion.ok, motion=motion, overlay_state=self.overlay_renderer.snapshot().__dict__, metadata={"kind": kind})
