from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .motion import MotionAction, MotionPoint


@dataclass(slots=True)
class PathProfile:
    steps: int
    kind: str
    hover_ms: int = 0
    drag_stable: bool = False
    curvature: float = 0.18


class PathGenerator:
    """Independent, testable path generation for virtual cursor motion."""

    def __init__(self, seed: int = 7) -> None:
        self._rng = Random(seed)

    @staticmethod
    def ease_value(ratio: float, easing: str = "ease_out_quad", accel: float = 1.0, decel: float = 1.0) -> float:
        ratio = max(0.0, min(1.0, ratio))
        if easing == "linear":
            return ratio
        if easing == "ease_in":
            return ratio ** max(accel, 0.1)
        if easing == "ease_out":
            return 1 - (1 - ratio) ** max(decel, 0.1)
        if easing == "ease_in_out":
            if ratio < 0.5:
                return 0.5 * (2 * ratio) ** max(accel, 0.1)
            return 1 - 0.5 * (2 * (1 - ratio)) ** max(decel, 0.1)
        if ratio < 0.5:
            return 0.5 * (2 * ratio) ** max(accel, 0.1)
        return 1 - 0.5 * (2 * (1 - ratio)) ** max(decel, 0.1)

    @staticmethod
    def bezier_point(start, control, end, t: float):
        from .motion import MotionPoint
        u = 1 - t
        x = round(u * u * start.x + 2 * u * t * control.x + t * t * end.x)
        y = round(u * u * start.y + 2 * u * t * control.y + t * t * end.y)
        return MotionPoint(x=x, y=y, t=t)

    @staticmethod
    def midpoint(start, end, curvature: float = 0.18):
        from .motion import MotionPoint
        dx = end.x - start.x
        dy = end.y - start.y
        return MotionPoint(x=round((start.x + end.x) / 2 - dy * curvature), y=round((start.y + end.y) / 2 + dx * curvature), t=0.5)

    @staticmethod
    def distance(start, end) -> float:
        return sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

    def sample_line(self, start, end, steps: int, *, easing: str, accel: float, decel: float):
        from .motion import MotionPoint
        steps = max(2, steps)
        points: list[MotionPoint] = []
        for index in range(steps):
            ratio = index / (steps - 1)
            eased = self.ease_value(ratio, easing=easing, accel=accel, decel=decel)
            points.append(MotionPoint(x=round(start.x + (end.x - start.x) * eased), y=round(start.y + (end.y - start.y) * eased), t=ratio))
        return points

    def sample_bezier(self, start, end, steps: int, *, curvature: float, easing: str, accel: float, decel: float):
        control = self.midpoint(start, end, curvature=curvature)
        steps = max(2, steps)
        points = []
        for index in range(steps):
            ratio = index / (steps - 1)
            eased = self.ease_value(ratio, easing=easing, accel=accel, decel=decel)
            points.append(self.bezier_point(start, control, end, eased))
        return points

    def hover_pause(self, start, hover_ms: int, steps: int = 4):
        from .motion import MotionPoint
        if hover_ms <= 0:
            return []
        count = max(2, min(steps, 6))
        return [MotionPoint(x=start.x + self._rng.randint(-1, 1), y=start.y + self._rng.randint(-1, 1), t=index / max(count - 1, 1)) for index in range(count)]

    def stabilize_drag(self, points: Iterable, strength: float = 0.25):
        from .motion import MotionPoint
        stabilized: list[MotionPoint] = []
        for index, point in enumerate(points):
            if index == 0:
                stabilized.append(point)
                continue
            prev = stabilized[-1]
            stabilized.append(MotionPoint(x=round(prev.x + (point.x - prev.x) * (1 - strength)), y=round(prev.y + (point.y - prev.y) * (1 - strength)), t=point.t))
        return stabilized

    def build(self, action, steps: int = 16):
        from .motion import MotionPoint
        steps = max(2, steps)
        path: list[MotionPoint] = []
        if action.hover_ms > 0:
            path.extend(self.hover_pause(action.start, action.hover_ms))
        distance = self.distance(action.start, action.end)
        if action.kind == "drag":
            first = self.sample_bezier(action.start, action.end, max(steps, 6), curvature=0.14, easing=action.easing, accel=action.accel, decel=action.decel)
            path.extend(self.stabilize_drag(first, strength=0.18))
        elif action.kind == "move":
            curvature = 0.22 if distance >= 120 else 0.12
            path.extend(self.sample_bezier(action.start, action.end, steps, curvature=curvature, easing="ease_in_out", accel=action.accel, decel=action.decel))
        elif action.kind == "click":
            prefix = self.sample_line(action.start, action.end, max(2, steps // 3), easing="ease_out", accel=action.accel, decel=action.decel)
            path.extend(prefix)
            path.append(MotionPoint(x=action.end.x, y=action.end.y, t=1.0))
        else:
            if distance >= 180:
                path.extend(self.sample_bezier(action.start, action.end, steps, curvature=0.16, easing=action.easing, accel=action.accel, decel=action.decel))
            else:
                path.extend(self.sample_line(action.start, action.end, steps, easing=action.easing, accel=action.accel, decel=action.decel))
        if not path:
            path = [action.start, action.end]
        return path
