from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.overlay import OverlayRenderer
from desktop_agent_dev.tool_registry import build_registry
from desktop_agent_dev.tool_specs.overlay_tools import register_overlay_tools


class DummyExecutor:
    def __init__(self) -> None:
        self._overlay_renderer = OverlayRenderer()
        self._overlay_renderer.show()
        self._overlay_renderer.update_cursor(12, 34)


class DummyServices(SimpleNamespace):
    pass


def test_overlay_state_registration() -> None:
    registry = build_registry()
    services = DummyServices(executor=DummyExecutor())

    register_overlay_tools(registry, services)

    spec = registry.get("overlay_state")
    assert spec.kind == "snapshot"
    assert spec.permission is None


def test_overlay_state_returns_snapshot() -> None:
    registry = build_registry()
    services = DummyServices(executor=DummyExecutor())
    services.executor._overlay_renderer.set_display_context(display_id="DISPLAY1", scale_factor=1.5, monitor_bounds=[{"left": 0, "top": 0, "right": 1920, "bottom": 1080}])
    services.executor._overlay_renderer.draw_click_ripple(12, 34)
    services.executor._overlay_renderer.set_drag_state(True, start={"x": 4, "y": 6})

    register_overlay_tools(registry, services)
    result = registry.get("overlay_state").executor()

    assert result["ok"] is True
    assert result["tool"] == "overlay_state"
    assert result["data"]["visible"] is True
    assert result["data"]["cursor_x"] == 12
    assert result["data"]["cursor_color"] == "#ff0000"
    assert result["data"]["cursor_size"] == 28
    assert result["data"]["persistent"] is True
    assert result["data"]["click_ripples"][0]["radius"] == 18
    assert result["data"]["drag_active"] is True
    assert result["data"]["display_id"] == "DISPLAY1"
    assert result["data"]["cursor_color"] == "#ff0000"
    assert result["data"]["user_cursor_color"] == "#3b82f6"
