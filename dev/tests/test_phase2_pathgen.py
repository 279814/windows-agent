from __future__ import annotations

from desktop_agent_dev.motion import MotionAction, MotionPoint
from desktop_agent_dev.pathgen import PathGenerator


def test_bezier_generation_returns_smooth_path() -> None:
    generator = PathGenerator(seed=7)
    start = MotionPoint(0, 0)
    end = MotionPoint(120, 60)

    points = generator.sample_bezier(start, end, 8, curvature=0.2, easing="ease_in_out", accel=1.2, decel=1.1)

    assert len(points) == 8
    assert points[0].x == 0 and points[0].y == 0
    assert points[-1].x == 120 and points[-1].y == 60
    assert any(point.y != 0 for point in points[1:-1])


def test_spline_generation_produces_more_controlled_curve() -> None:
    generator = PathGenerator(seed=7)
    start = MotionPoint(5, 5)
    end = MotionPoint(300, 180)

    points = generator.sample_spline(start, end, 12, curvature=0.18, easing="ease_in_out", accel=1.0, decel=1.0)

    assert len(points) >= 12
    assert points[0].x == 5 and points[0].y == 5
    assert points[-1].x == 300 and points[-1].y == 180
    assert len({(point.x, point.y) for point in points}) > 3


def test_sampling_and_easing_behave_monotonically() -> None:
    generator = PathGenerator(seed=7)
    start = MotionPoint(0, 0)
    end = MotionPoint(100, 100)

    line = generator.sample_line(start, end, 5, easing="ease_in", accel=2.0, decel=1.0)
    assert line[0].x == 0
    assert line[-1].x == 100
    assert line[1].x - line[0].x < line[-1].x - line[-2].x

    assert generator.ease_value(0.2, easing="ease_in") < generator.ease_value(0.8, easing="ease_in")
    assert generator.ease_value(0.2, easing="ease_out") < generator.ease_value(0.8, easing="ease_out")


def test_drag_stabilization_and_hover_pause_are_deterministic_enough() -> None:
    generator = PathGenerator(seed=7)
    action = MotionAction(kind="drag", start=MotionPoint(10, 10), end=MotionPoint(180, 140), hover_ms=40)

    path = generator.build(action, steps=10)
    hover = generator.hover_pause(action.start, 40)
    stabilized = generator.stabilize_drag([MotionPoint(10, 10), MotionPoint(20, 20), MotionPoint(40, 40)])

    assert len(hover) >= 2
    assert len(path) >= 10
    assert stabilized[1].x < 20 and stabilized[1].y < 20
    assert path[-1].x == 180 and path[-1].y == 140


def test_long_distance_uses_richer_path_than_short_distance() -> None:
    generator = PathGenerator(seed=7)
    short_action = MotionAction(kind="move", start=MotionPoint(0, 0), end=MotionPoint(20, 20))
    long_action = MotionAction(kind="move", start=MotionPoint(0, 0), end=MotionPoint(400, 220))

    short_path = generator.build(short_action, steps=6)
    long_path = generator.build(long_action, steps=6)

    assert len(short_path) == 6
    assert len(long_path) >= 6
    assert len({(p.x, p.y) for p in long_path}) >= len({(p.x, p.y) for p in short_path})
