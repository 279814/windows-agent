from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.executor import Executor
from desktop_agent_dev.overlay import OverlayRenderer
from desktop_agent_dev.motion import MotionScheduler
from desktop_agent_dev.user_input_monitor import NativeUserTakeoverMonitor


class CancelBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.focused = {"name": "Editor", "window_title": "Editor", "handle": 101, "pid": 202, "status": "NORMAL", "is_visible": True}
        self.focused_control = {"name": "Field", "window_title": "Editor", "value": "before", "bounds": [10, 10, 110, 30]}

    def get_state(self, use_vision: bool = False, as_bytes: bool = False):
        return SimpleNamespace(focused_control=self.focused_control, active_window=self.focused, display_id="MON-1", dpi_scale=1.0, monitor_bounds=[])

    def move(self, loc):
        self.calls.append(("move", loc))

    def click(self, loc, button="left", clicks=1):
        self.calls.append(("click", loc, button, clicks))

    def drag(self, loc):
        self.calls.append(("drag", loc))

    def focus_app(self, name):
        self.calls.append(("focus", name))
        return (f"Focused {name}.", 0)


class FakeInterruptionMonitor(NativeUserTakeoverMonitor):
    def __init__(self, reasons: list[str | None]) -> None:
        super().__init__()
        self._reasons = list(reasons)

    def begin(self, *, expected_cursor=None, enable_pointer_drift: bool = False) -> None:
        return None

    def end(self) -> None:
        return None

    def reason(self, *, expected_cursor=None) -> str | None:
        if self._reasons:
            return self._reasons.pop(0)
        return None


def test_click_exports_timeline_and_target_verification() -> None:
    executor = Executor(backend=CancelBackend(), overlay_renderer=OverlayRenderer(), motion_scheduler=MotionScheduler(debug_show_points=True, debug_show_target=True))

    result = executor.click(50, 60)

    assert result.ok is True
    assert result.payload["execution_timeline"]
    assert result.payload["target_verification"]["ok"] is True
    assert result.payload["overlay_state"]["timeline"]


def test_drag_exports_timeline_and_target_verification() -> None:
    executor = Executor(backend=CancelBackend(), overlay_renderer=OverlayRenderer(), motion_scheduler=MotionScheduler(debug_show_points=True, debug_show_target=True))

    result = executor.drag((10, 10), (100, 120))

    assert result.ok is True
    assert result.payload["execution_timeline"]
    assert result.payload["target_verification"]["ok"] is True
    assert result.payload["overlay_state"]["drag_active"] is False


def test_motion_execute_exports_unified_timeline_and_supports_local_cancel() -> None:
    executor = Executor(
        backend=CancelBackend(),
        overlay_renderer=OverlayRenderer(),
        motion_scheduler=MotionScheduler(debug_show_points=True, debug_show_target=True),
        interruption_monitor=FakeInterruptionMonitor([None, None, "mouse_button"]),
    )

    result = executor.motion_execute("move", (0, 0), (40, 40))

    assert result["ok"] is False
    assert result["phase"] == "cancelled"
    assert result["execution_timeline"]
    assert any(item["data"].get("category") == "motion" for item in result["execution_timeline"])
