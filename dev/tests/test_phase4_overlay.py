from __future__ import annotations

from desktop_agent_dev.overlay import OverlayRenderer


class FakePresenter:
    def __init__(self) -> None:
        self.frames = []
        self.closed = False

    def publish(self, frame) -> None:
        self.frames.append(frame)

    def close(self) -> None:
        self.closed = True


def test_overlay_tracks_pointer_trail_click_ripples_and_drag_state() -> None:
    overlay = OverlayRenderer()
    overlay.update_cursor(10, 20)
    overlay.update_cursor(12, 24)
    overlay.set_target(40, 50, visible=True)
    overlay.set_pressed(True)
    overlay.set_status_text("animating")
    overlay.draw_click_ripple(12, 24, radius=22)
    overlay.set_drag_state(True, start={"x": 10, "y": 20})

    snapshot = overlay.snapshot()

    assert snapshot.visible is True
    assert snapshot.cursor_x == 12
    assert snapshot.cursor_y == 24
    assert snapshot.cursor_size > snapshot.user_cursor_size
    assert snapshot.persistent is True
    assert snapshot.target_visible is True
    assert snapshot.target_x == 40
    assert snapshot.target_y == 50
    assert snapshot.status_text == "animating"
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
    assert snapshot.cursor_color == "#5eead4"
    assert snapshot.cursor_size == 24
    assert snapshot.user_cursor_size == 14
    assert snapshot.persistent is True


def test_overlay_pointer_shape_and_colorref_helpers_are_stable() -> None:
    overlay = OverlayRenderer()
    overlay.update_cursor(64, 96)

    shape = overlay.render_pointer_shape()

    assert len(shape["body"]) == 7
    assert len(shape["shadow"]) == 7
    assert len(shape["accent"]) == 3


def test_overlay_window_colorref_matches_windows_bgr_layout() -> None:
    from desktop_agent_dev.overlay_window import TkOverlayWindow

    assert TkOverlayWindow._colorref("#010203") == 0x030201


def test_overlay_window_pointer_polygon_geometry_is_stable() -> None:
    from desktop_agent_dev.overlay_window import TkOverlayWindow

    points = TkOverlayWindow._pointer_polygon_points(40, 36, 14, 36, 24)

    assert len(points) == 14
    assert points[0:2] == [40, 36]
    assert max(points[::2]) > 40
    assert max(points[1::2]) > 36


def test_overlay_window_status_badge_visibility_is_scoped() -> None:
    from desktop_agent_dev.overlay_window import TkOverlayWindow

    assert TkOverlayWindow._should_draw_status_badge("idle", pressed=False) is False
    assert TkOverlayWindow._should_draw_status_badge("animating", pressed=False) is False
    assert TkOverlayWindow._should_draw_status_badge("verifying", pressed=False) is True
    assert TkOverlayWindow._should_draw_status_badge("failed", pressed=False) is True
    assert TkOverlayWindow._should_draw_status_badge("anything", pressed=True) is True


def test_overlay_publishes_snapshots_to_desktop_presenter() -> None:
    presenter = FakePresenter()
    overlay = OverlayRenderer(presenter=presenter)

    overlay.update_cursor(30, 40)
    overlay.set_style(cursor_size=32, persistent=True)
    overlay.close()

    assert presenter.frames
    assert presenter.frames[-1].cursor_x == 30
    assert presenter.frames[-1].cursor_size == 32
    assert presenter.closed is True
