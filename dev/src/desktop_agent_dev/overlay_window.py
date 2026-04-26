from __future__ import annotations

import atexit
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from queue import Empty, Queue
import threading
from typing import Protocol

try:
    import tkinter as tk
except Exception:  # pragma: no cover - tkinter may be unavailable in some environments
    tk = None  # type: ignore[assignment]


SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
GWL_EXSTYLE = -20
GWL_WNDPROC = -4
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_DISABLED = 0x08000000
LWA_COLORKEY = 0x00000001
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1


class OverlayWindowPresenter(Protocol):
    def publish(self, frame: object) -> None:
        ...

    def close(self) -> None:
        ...


class NativeOverlayWindowController:
    """Native Win32 helper for geometry and click-through behavior."""

    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32 if os.name == "nt" else None
        self._old_wndproc = None
        self._wndproc = None

    def virtual_screen_geometry(self) -> tuple[int, int, int, int]:
        if self._user32 is None:
            return 0, 0, 1, 1
        left = int(self._user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        top = int(self._user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        width = int(self._user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        height = int(self._user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        return left, top, max(1, width), max(1, height)

    def clamp_window_rect(self, *, left: int, top: int, width: int, height: int) -> tuple[int, int]:
        screen_left, screen_top, screen_width, screen_height = self.virtual_screen_geometry()
        screen_right = screen_left + screen_width
        screen_bottom = screen_top + screen_height
        clamped_left = min(max(left, screen_left), max(screen_left, screen_right - width))
        clamped_top = min(max(top, screen_top), max(screen_top, screen_bottom - height))
        return clamped_left, clamped_top

    def make_click_through(self, root: tk.Tk, bg: str) -> None:
        if self._user32 is None:
            return
        hwnd = wintypes.HWND(root.winfo_id())
        get_window_long_ptr = getattr(self._user32, "GetWindowLongPtrW", self._user32.GetWindowLongW)
        set_window_long_ptr = getattr(self._user32, "SetWindowLongPtrW", self._user32.SetWindowLongW)
        ex_style = get_window_long_ptr(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        set_window_long_ptr(hwnd, GWL_EXSTYLE, ex_style)
        root.wm_attributes("-disabled", True)
        self._user32.SetLayeredWindowAttributes(hwnd, ctypes.c_uint(self.colorref(bg)), 0, LWA_COLORKEY)
        self._install_transparent_hit_test(hwnd)
        self._user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED)

    def _install_transparent_hit_test(self, hwnd: wintypes.HWND) -> None:
        if self._user32 is None:
            return
        get_window_long_ptr = getattr(self._user32, "GetWindowLongPtrW", self._user32.GetWindowLongW)
        set_window_long_ptr = getattr(self._user32, "SetWindowLongPtrW", self._user32.SetWindowLongW)
        call_window_proc = self._user32.CallWindowProcW
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        @WNDPROC
        def wndproc(window_handle, message, w_param, l_param):
            if message == WM_NCHITTEST:
                return HTTRANSPARENT
            return call_window_proc(self._old_wndproc, window_handle, message, w_param, l_param)

        self._wndproc = wndproc
        self._old_wndproc = get_window_long_ptr(hwnd, GWL_WNDPROC)
        set_window_long_ptr(hwnd, GWL_WNDPROC, wndproc)

    @staticmethod
    def colorref(color: str) -> int:
        value = color.lstrip("#")
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
        return red | (green << 8) | (blue << 16)


@dataclass(slots=True)
class OverlayWindowFrame:
    visible: bool
    cursor_x: int
    cursor_y: int
    cursor_color: str
    user_cursor_color: str
    cursor_size: int
    user_cursor_size: int
    persistent: bool
    pressed: bool
    target_x: int | None
    target_y: int | None
    target_visible: bool
    status_text: str
    trail: list[tuple[int, int]]
    click_ripples: list[dict[str, int]]


def overlay_window_enabled() -> bool:
    env_value = os.environ.get("DESKTOP_AGENT_DEV_OVERLAY_WINDOW")
    if env_value is not None:
        return env_value.strip().lower() not in {"0", "false", "no", "off"}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return os.name == "nt"


class TkOverlayWindow:
    """Draws the virtual cursor in a transparent always-on-top desktop window."""

    _WINDOW_SIZE = 180
    _CURSOR_MARGIN_LEFT = 28
    _CURSOR_MARGIN_TOP = 26
    _TARGET_RING_COUNT = 2

    def __init__(self) -> None:
        self._queue: Queue[OverlayWindowFrame | None] = Queue()
        self._thread: threading.Thread | None = None
        self._started = False
        self._lock = threading.Lock()
        self._available = tk is not None and os.name == "nt"
        self._closed = False
        self._bg = "#010203"
        self._native = NativeOverlayWindowController()

    def publish(self, frame: object) -> None:
        if self._closed or not self._available:
            return
        overlay_frame = OverlayWindowFrame(
            visible=bool(getattr(frame, "visible", True)),
            cursor_x=int(getattr(frame, "cursor_x", 0)),
            cursor_y=int(getattr(frame, "cursor_y", 0)),
            cursor_color=str(getattr(frame, "cursor_color", "#5eead4")),
            user_cursor_color=str(getattr(frame, "user_cursor_color", "#f59e0b")),
            cursor_size=int(getattr(frame, "cursor_size", 24)),
            user_cursor_size=int(getattr(frame, "user_cursor_size", 14)),
            persistent=bool(getattr(frame, "persistent", True)),
            pressed=bool(getattr(frame, "pressed", False)),
            target_x=getattr(frame, "target_x", None),
            target_y=getattr(frame, "target_y", None),
            target_visible=bool(getattr(frame, "target_visible", False)),
            status_text=str(getattr(frame, "status_text", "idle")),
            trail=list(getattr(frame, "trail", [])),
            click_ripples=[dict(ripple) for ripple in getattr(frame, "click_ripples", [])],
        )
        self._ensure_started()
        self._queue.put(overlay_frame)

    def close(self) -> None:
        self._closed = True
        if not self._available:
            return
        self._queue.put(None)

    def _ensure_started(self) -> None:
        with self._lock:
            if self._started or not self._available:
                return
            self._started = True
            self._thread = threading.Thread(target=self._run, name="desktop-agent-overlay", daemon=True)
            self._thread.start()
            atexit.register(self.close)

    def _run(self) -> None:  # pragma: no cover - exercised manually on Windows desktop
        try:
            root = tk.Tk()
            root.withdraw()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(bg=self._bg)
            try:
                root.wm_attributes("-transparentcolor", self._bg)
            except Exception:
                pass
            width = self._WINDOW_SIZE
            height = self._WINDOW_SIZE
            left = 0
            top = 0
            root.geometry(f"{width}x{height}+{left}+{top}")
            canvas = tk.Canvas(root, bg=self._bg, highlightthickness=0, bd=0)
            canvas.place(x=0, y=0, width=width, height=height)
            root.deiconify()
            self._make_click_through(root)

            def pump() -> None:
                try:
                    latest: OverlayWindowFrame | None = None
                    while True:
                        latest = self._queue.get_nowait()
                except Empty:
                    latest = latest if "latest" in locals() else None
                if latest is None:
                    if self._closed:
                        try:
                            root.destroy()
                        except Exception:
                            pass
                        return
                else:
                    self._render(root, canvas, latest)
                root.after(16, pump)

            pump()
            root.mainloop()
        except Exception:
            self._available = False

    def _render(self, root: tk.Tk, canvas: tk.Canvas, frame: OverlayWindowFrame) -> None:
        canvas.delete("all")
        should_draw = frame.visible or frame.persistent
        if not should_draw:
            return
        width = self._WINDOW_SIZE
        height = self._WINDOW_SIZE
        desired_left = int(frame.cursor_x) - self._CURSOR_MARGIN_LEFT
        desired_top = int(frame.cursor_y) - self._CURSOR_MARGIN_TOP
        left, top = self._native.clamp_window_rect(left=desired_left, top=desired_top, width=width, height=height)
        root.geometry(f"{width}x{height}+{left}+{top}")
        x = int(frame.cursor_x) - left
        y = int(frame.cursor_y) - top
        radius = max(6, frame.cursor_size // 2)
        trail = [(point[0] - left, point[1] - top) for point in frame.trail[-12:]]
        if frame.target_visible and frame.target_x is not None and frame.target_y is not None:
            target_x = int(frame.target_x) - left
            target_y = int(frame.target_y) - top
            distance_sq = (target_x - x) ** 2 + (target_y - y) ** 2
            if distance_sq > 28 * 28:
                self._draw_target_beacon(canvas, target_x, target_y, radius=radius + 6, color=frame.cursor_color)
                self._draw_connector(canvas, x + 7, y + 16, target_x, target_y, color=frame.cursor_color)
        if len(trail) >= 2:
            self._draw_trail(canvas, trail, color=frame.cursor_color, radius=radius)
        for ripple in frame.click_ripples[-3:]:
            ripple_x = int(ripple.get("x", 0)) - left
            ripple_y = int(ripple.get("y", 0)) - top
            ripple_radius = max(10, int(ripple.get("radius", 18)))
            self._draw_click_ripple(canvas, ripple_x, ripple_y, ripple_radius, color=frame.cursor_color)
        self._draw_pointer(canvas, x=x, y=y, size=frame.cursor_size, color=frame.cursor_color, pressed=frame.pressed)
        if self._should_draw_status_badge(frame.status_text, pressed=frame.pressed):
            badge_text = frame.status_text[:24]
            badge_w = max(74, 10 + len(badge_text) * 6)
            badge_x = min(18, max(6, x - 10))
            badge_y = min(76, max(6, y + 42))
            canvas.create_rectangle(
                badge_x,
                badge_y,
                badge_x + badge_w,
                badge_y + 20,
                fill="#0f172a",
                outline=self._blend(frame.cursor_color, self._bg, 0.72),
                width=1,
            )
            canvas.create_text(
                badge_x + 8,
                badge_y + 10,
                text=badge_text,
                fill=self._blend("#f8fafc", self._bg, 0.22),
                anchor="w",
                font=("Segoe UI", 8, "normal"),
            )

    def _draw_target_beacon(self, canvas: tk.Canvas, x: int, y: int, *, radius: int, color: str) -> None:
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=self._blend(color, "#ffffff", 0.15), outline="")
        for index in range(self._TARGET_RING_COUNT):
            current_radius = radius + index * 7
            blend_ratio = 0.46 + index * 0.16
            canvas.create_oval(
                x - current_radius,
                y - current_radius,
                x + current_radius,
                y + current_radius,
                outline=self._blend(color, self._bg, blend_ratio),
                width=1,
            )
        canvas.create_line(x - 5, y, x + 5, y, fill=self._blend(color, self._bg, 0.52), width=1)
        canvas.create_line(x, y - 5, x, y + 5, fill=self._blend(color, self._bg, 0.52), width=1)

    def _draw_connector(self, canvas: tk.Canvas, start_x: int, start_y: int, end_x: int, end_y: int, *, color: str) -> None:
        mid_x = round((start_x + end_x) / 2)
        control_y = min(start_y, end_y) - 10
        canvas.create_line(
            start_x,
            start_y,
            mid_x,
            control_y,
            end_x,
            end_y,
            smooth=True,
            splinesteps=18,
            fill=self._blend(color, self._bg, 0.62),
            width=1,
        )

    def _draw_trail(self, canvas: tk.Canvas, trail: list[tuple[int, int]], *, color: str, radius: int) -> None:
        if len(trail) < 2:
            return
        flattened: list[int] = []
        for trail_x, trail_y in trail:
            flattened.extend((trail_x, trail_y))
        canvas.create_line(
            *flattened,
            smooth=True,
            splinesteps=24,
            fill=self._blend(color, self._bg, 0.7),
            width=max(1, radius // 5),
        )
        for index, (trail_x, trail_y) in enumerate(trail):
            progress = (index + 1) / len(trail)
            dot_radius = max(1, round(1 + progress * 2))
            dot_color = self._blend(color, self._bg, max(0.16, 0.8 - progress * 0.42))
            canvas.create_oval(
                trail_x - dot_radius,
                trail_y - dot_radius,
                trail_x + dot_radius,
                trail_y + dot_radius,
                fill=dot_color,
                outline="",
            )

    def _draw_click_ripple(self, canvas: tk.Canvas, x: int, y: int, radius: int, *, color: str) -> None:
        for index, extra in enumerate((0, 8)):
            ripple_radius = radius + extra
            canvas.create_oval(
                x - ripple_radius,
                y - ripple_radius,
                x + ripple_radius,
                y + ripple_radius,
                outline=self._blend(color, self._bg, 0.34 + index * 0.14),
                width=1,
            )

    def _draw_pointer(self, canvas: tk.Canvas, *, x: int, y: int, size: int, color: str, pressed: bool) -> None:
        pointer_height = size + 8
        pointer_width = max(10, round(size * 0.56))
        shadow_offset = 3 if pressed else 2
        shadow = self._pointer_polygon_points(x + shadow_offset, y + shadow_offset, pointer_width, pointer_height, size)
        body = self._pointer_polygon_points(x, y, pointer_width, pointer_height, size)
        accent = [
            x + round(pointer_width * 0.18),
            y + round(pointer_height * 0.18),
            x + round(pointer_width * 0.18),
            y + round(pointer_height * 0.84),
            x + round(pointer_width * 0.56),
            y + round(pointer_height * 0.62),
        ]
        inner_edge = [
            x + round(pointer_width * 0.12),
            y + round(pointer_height * 0.22),
            x + round(pointer_width * 0.12),
            y + round(pointer_height * 0.7),
            x + round(pointer_width * 0.36),
            y + round(pointer_height * 0.55),
        ]
        canvas.create_polygon(shadow, fill=self._blend("#020617", self._bg, 0.12), outline="")
        canvas.create_polygon(body, fill="#f8fafc", outline=color, width=2 if pressed else 1, joinstyle="round")
        canvas.create_polygon(accent, fill=self._blend(color, "#ffffff", 0.38), outline="")
        canvas.create_line(*inner_edge, fill=self._blend("#ffffff", color, 0.26), width=1)

    @staticmethod
    def _should_draw_status_badge(status_text: str, *, pressed: bool) -> bool:
        normalized = status_text.strip().lower()
        if pressed:
            return True
        return normalized in {"failed", "drag", "dragging", "verifying"}

    @staticmethod
    def _pointer_polygon_points(x: int, y: int, width: int, height: int, size: int) -> list[int]:
        return [
            x,
            y,
            x,
            y + height,
            x + width,
            y + round(height * 0.62),
            x + round(width * 0.54),
            y + round(height * 0.5),
            x + round(width * 0.76),
            y + height + round(size * 0.28),
            x + round(width * 0.34),
            y + height + round(size * 0.38),
            x + round(width * 0.1),
            y + round(height * 0.68),
        ]

    def _make_click_through(self, root: tk.Tk) -> None:
        try:
            self._native.make_click_through(root, self._bg)
        except Exception:
            return

    @staticmethod
    def _blend(color: str, background: str, ratio: float) -> str:
        def _rgb(hex_color: str) -> tuple[int, int, int]:
            value = hex_color.lstrip("#")
            return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

        ratio = max(0.0, min(1.0, ratio))
        r1, g1, b1 = _rgb(color)
        r2, g2, b2 = _rgb(background)
        r = round(r1 * (1 - ratio) + r2 * ratio)
        g = round(g1 * (1 - ratio) + g2 * ratio)
        b = round(b1 * (1 - ratio) + b2 * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _colorref(color: str) -> int:
        return NativeOverlayWindowController.colorref(color)
