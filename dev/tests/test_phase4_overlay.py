from __future__ import annotations

from desktop_agent_dev.overlay import OverlayRenderer


def test_overlay_tracks_pointer_trail_click_ripples_and_drag_state() -> None:
    overlay = OverlayRenderer()
    overlay.update_cursor(10, 20)
    overlay.update_cursor(12, 24)
    overlay.draw_click_ripple(12, 24, radius=22)
    overlay.set_drag_state(True, start={"x": 10, "y": 20})

    snapshot = overlay.snapshot()

    assert snapshot.visible is True
    assert snapshot.cursor_x == 12
    assert snapshot.cursor_y == 24
    assert snapshot.cursor_size > snapshot.user_cursor_size
    assert snapshot.persistent is True
    assert snapshot.trail[-1] == (12, 24)
    assert snapshot.click_ripples[0]["radius"] == 22
    assert snapshot.drag_active is True
    assert snapshot.drag_start == {"x": 10, "y": 20}


def test_overlay_supports_display_context_and_scaling() -> None:
    overlay = OverlayRenderer()
    overlay.set_display_context(
        display_id="MON-1",
        scale_factor=1.25,
        monitor_bounds=[{"left": 0, "top": 0, "right": 2560, "bottom": 1440}],
    )

    snapshot = overlay.snapshot()

    assert snapshot.display_id == "MON-1"
    assert snapshot.scale_factor == 1.25
    assert snapshot.monitor_bounds[0]["right"] == 2560


def test_overlay_defaults_to_persistent_large_red_virtual_cursor() -> None:
    overlay = OverlayRenderer()

    snapshot = overlay.snapshot()

    assert snapshot.visible is True
    assert snapshot.cursor_color == "#ff0000"
    assert snapshot.cursor_size == 28
    assert snapshot.user_cursor_size == 14
    assert snapshot.persistent is True
