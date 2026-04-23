from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.executor import Executor
from desktop_agent_dev.overlay import OverlayRenderer


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


def test_click_updates_overlay_and_uses_backend() -> None:
    executor = Executor(backend=FakeBackend(), overlay_renderer=OverlayRenderer())

    result = executor.click(100, 200)

    assert result.ok is True
    assert result.payload["overlay_state"]["visible"] is True
    assert result.payload["overlay_state"]["click_ripples"]
    assert result.payload["overlay_state"]["cursor_x"] == 100


def test_focus_and_type_publish_overlay_state() -> None:
    executor = Executor(backend=FakeBackend(), overlay_renderer=OverlayRenderer())

    focus_result = executor.focus_window("Editor")
    type_result = executor.type_text("hello")

    assert focus_result.ok is True
    assert focus_result.payload["overlay_state"]["display_id"] == "MON-1"
    assert type_result.ok is True
    assert type_result.payload["overlay_state"]["last_action_kind"] == "type"
    assert type_result.payload["overlay_state"]["scale_factor"] == 1.5
