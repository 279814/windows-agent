from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.motion import MotionScheduler
from desktop_agent_dev.overlay import OverlayRenderer
from desktop_agent_dev.tool_registry import build_registry
from desktop_agent_dev.tool_specs.motion_tools import register_motion_tools


class DummySafety:
    def check(self, _permission: str) -> bool:
        return True


class DummyExecutor:
    def __init__(self) -> None:
        self.calls = []
        self._motion_scheduler = MotionScheduler()
        self._overlay_renderer = OverlayRenderer()

    def motion_preview(self, kind, start, end, duration_ms=None, steps=16):
        self.calls.append((kind, start, end, duration_ms, steps))
        return {
            "ok": True,
            "phase": "verified",
            "action": {"kind": kind, "start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}, "duration_ms": duration_ms or 180, "easing": "ease_out_quad", "metadata": {}},
            "path": [{"x": start[0], "y": start[1], "t": 0.0}, {"x": end[0], "y": end[1], "t": 1.0}],
            "detail": "motion planned",
            "metadata": {"steps": 2},
            "overlay_state": {"visible": False, "cursor_x": end[0], "cursor_y": end[1], "trail": [start, end], "metadata": {}},
        }


class DummyServices(SimpleNamespace):
    pass


def test_motion_preview_registration_adds_new_tool() -> None:
    registry = build_registry()
    services = DummyServices(executor=DummyExecutor(), safety=DummySafety())

    register_motion_tools(registry, services)

    spec = registry.get("motion_preview")
    assert spec.kind == "motion"
    assert spec.permission == "motion_preview"
    assert spec.input_examples == [{"kind": "drag", "start_x": 10, "start_y": 10, "end_x": 100, "end_y": 100}]


def test_motion_preview_executor_returns_overlay_state() -> None:
    registry = build_registry()
    services = DummyServices(executor=DummyExecutor(), safety=DummySafety())

    register_motion_tools(registry, services)
    result = registry.get("motion_preview").executor("drag", 10, 10, 100, 100)

    assert result["ok"] is True
    assert result["tool"] == "motion_preview"
    assert result["data"]["payload"]["overlay_state"]["cursor_x"] == 100
    assert result["data"]["payload"]["path"][-1]["x"] == 100


def test_motion_preview_is_read_only_for_overlay_cursor() -> None:
    from desktop_agent_dev.executor import Executor

    executor = Executor(overlay_renderer=OverlayRenderer(), motion_scheduler=MotionScheduler())
    executor._overlay_renderer.update_cursor(12, 34)

    result = executor.motion_preview("move", (12, 34), (100, 120))

    snapshot = executor._overlay_renderer.snapshot()

    assert result["ok"] is True
    assert result["overlay_state"]["cursor_x"] == 12
    assert result["overlay_state"]["metadata"]["preview_only"] is True
    assert snapshot.cursor_x == 12
    assert snapshot.cursor_y == 34
