from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.executor import Executor
from desktop_agent_dev.overlay import OverlayRenderer
from desktop_agent_dev.user_input_monitor import NativeUserTakeoverMonitor


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, int] | str]] = []
        self.focused = {"name": "Editor", "window_title": "Editor", "handle": 101, "pid": 202, "status": "NORMAL", "is_visible": True}
        self.focused_control = {"name": "Field", "window_title": "Editor", "value": "before", "bounds": [10, 10, 110, 30]}

    def get_state(self, use_vision: bool = False, as_bytes: bool = False):
        return SimpleNamespace(focused_control=self.focused_control, active_window=self.focused, display_id="MON-1", dpi_scale=1.5, monitor_bounds=[{"left": 0, "top": 0, "right": 1920, "bottom": 1080}])

    def click(self, loc, button="left", clicks=1):
        self.calls.append(("click", loc))

    def move(self, loc):
        self.calls.append(("move", loc))

    def drag(self, loc):
        self.calls.append(("drag", loc))

    def type(self, loc, text, press_enter=False, clear=False, caret_position="idle"):
        self.calls.append(("type", text))
        self.focused_control = {"name": "Field", "window_title": "Editor", "value": text, "bounds": [10, 10, 110, 30]}

    def shortcut(self, keys):
        self.calls.append(("shortcut", keys))

    def focus_app(self, name):
        self.calls.append(("focus", name))
        self.focused = {"name": name, "window_title": name, "handle": 101, "pid": 202, "status": "NORMAL", "is_visible": True}
        return (f"Focused {name}.", 0)

    def close_app(self, name):
        self.calls.append(("close", name))
        return (f"Closed {name}.", 0)


class NoopInterruptionMonitor(NativeUserTakeoverMonitor):
    def begin(self, *, expected_cursor=None, enable_pointer_drift: bool = False) -> None:
        return None

    def end(self) -> None:
        return None

    def reason(self, *, expected_cursor=None) -> str | None:
        return None


def test_click_updates_overlay_and_uses_backend() -> None:
    executor = Executor(backend=FakeBackend(), overlay_renderer=OverlayRenderer(), interruption_monitor=NoopInterruptionMonitor())

    result = executor.click(100, 200)

    assert result.ok is True
    assert result.payload["overlay_state"]["visible"] is True
    assert result.payload["overlay_state"]["click_ripples"]
    assert result.payload["overlay_state"]["cursor_x"] == 150
    assert result.payload["overlay_state"]["target_visible"] is True
    assert result.payload["overlay_state"]["status_text"] in {"verified", "click"}
    assert result.payload["phase"] == "verified"
    assert result.payload["action"]["kind"] == "click"
    assert result.payload["event"]["phase"] == "verified"
    assert set(result.payload["motion_segments"]) == {"hover", "settle", "execute"}


def test_move_reaches_backend_without_unboundlocal_error() -> None:
    backend = FakeBackend()
    executor = Executor(backend=backend, overlay_renderer=OverlayRenderer(), interruption_monitor=NoopInterruptionMonitor())

    result = executor.move(100, 200)

    assert result.ok is True
    assert ("move", (150, 300)) in backend.calls
    assert result.payload["target_verification"]["ok"] is True
    assert result.payload["overlay_state"]["persistent"] is True
    assert result.payload["overlay_state"]["target_x"] == 150
    assert result.payload["overlay_state"]["target_y"] == 300
    assert result.payload["phase"] == "verified"
    assert result.payload["action"]["kind"] == "move"
    assert result.payload["motion"]["path"] == result.payload["path"]
    assert set(result.payload["motion_segments"]) == {"execute"}


def test_focus_and_type_publish_overlay_state() -> None:
    executor = Executor(backend=FakeBackend(), overlay_renderer=OverlayRenderer(), interruption_monitor=NoopInterruptionMonitor())

    focus_result = executor.focus_window("Editor")
    type_result = executor.type_text("hello")

    assert focus_result.ok is True
    assert focus_result.payload["overlay_state"]["display_id"] == "MON-1"
    assert type_result.ok is True
    assert type_result.payload["overlay_state"]["last_action_kind"] == "type"
    assert type_result.payload["overlay_state"]["scale_factor"] == 1.5


def test_drag_runs_with_normalized_coordinates() -> None:
    backend = FakeBackend()
    executor = Executor(backend=backend, overlay_renderer=OverlayRenderer(), interruption_monitor=NoopInterruptionMonitor())

    result = executor.drag((10, 10), (100, 120))

    assert result.ok is True
    assert ("move", (15, 15)) in backend.calls
    assert ("drag", (150, 180)) in backend.calls
    assert result.payload["overlay_state"]["target_x"] == 150
    assert result.payload["overlay_state"]["target_y"] == 180
    assert result.payload["phase"] == "verified"
    assert result.payload["action"]["kind"] == "drag"
    assert result.payload["event"]["phase"] == "verified"
    assert set(result.payload["motion_segments"]) == {"hover", "execute"}
