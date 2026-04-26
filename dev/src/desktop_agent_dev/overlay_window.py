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
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x00000001
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class OverlayWindowPresenter(Protocol):
    def publish(self, frame: object) -> None:
        ...

    def close(self) -> None:
        ...


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

    def __init__(self) -> None:
        self._queue: Queue[OverlayWindowFrame | None] = Queue()
        self._thread: threading.Thread | None = None
        self._started = False
        self._lock = threading.Lock()
        self._available = tk is not None and os.name == "nt"
        self._closed = False
        self._bg = "#010203"

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
            left, top, width, height = self._virtual_screen_geometry()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(bg=self._bg)
            try:
                root.wm_attributes("-transparentcolor", self._bg)
            except Exception:
                pass
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
                    self._render(canvas, latest, left=left, top=top)
                root.after(16, pump)

            pump()
            root.mainloop()
        except Exception:
            self._available = False

    def _render(self, canvas: tk.Canvas, frame: OverlayWindowFrame, *, left: int, top: int) -> None:
        canvas.delete("all")
        should_draw = frame.visible or frame.persistent
        if not should_draw:
            return
        x = frame.cursor_x - left
        y = frame.cursor_y - top
        radius = max(8, frame.cursor_size // 2)
        trail = [(point[0] - left, point[1] - top) for point in frame.trail[-12:]]
        if frame.target_visible and frame.target_x is not None and frame.target_y is not None:
            target_x = int(frame.target_x) - left
            target_y = int(frame.target_y) - top
            target_radius = radius + 14
            canvas.create_oval(target_x - target_radius, target_y - target_radius, target_x + target_radius, target_y + target_radius, outline=self._blend(frame.cursor_color, self._bg, 0.35), width=2)
            canvas.create_oval(target_x - target_radius - 8, target_y - target_radius - 8, target_x + target_radius + 8, target_y + target_radius + 8, outline=self._blend(frame.cursor_color, self._bg, 0.55), width=1)
        if len(trail) >= 2:
            for index in range(1, len(trail)):
                opacity = index / len(trail)
                color = self._blend(frame.cursor_color, self._bg, max(0.15, 0.85 - opacity * 0.65))
                x1, y1 = trail[index - 1]
                x2, y2 = trail[index]
                canvas.create_line(x1, y1, x2, y2, fill=color, width=max(2, radius // 4), smooth=True)
        for ripple in frame.click_ripples[-3:]:
            ripple_x = int(ripple.get("x", 0)) - left
            ripple_y = int(ripple.get("y", 0)) - top
            ripple_radius = max(10, int(ripple.get("radius", 18)))
            canvas.create_oval(
                ripple_x - ripple_radius,
                ripple_y - ripple_radius,
                ripple_x + ripple_radius,
                ripple_y + ripple_radius,
                outline=self._blend(frame.cursor_color, self._bg, 0.25),
                width=2,
            )
        pointer_height = frame.cursor_size + 10
        pointer_width = max(10, round(frame.cursor_size * 0.58))
        shadow = [
            x + 2,
            y + 3,
            x + 2,
            y + pointer_height + 3,
            x + pointer_width + 2,
            y + round(pointer_height * 0.66) + 3,
            x + round(pointer_width * 0.52) + 2,
            y + round(pointer_height * 0.54) + 3,
            x + round(pointer_width * 0.72) + 2,
            y + pointer_height + round(frame.cursor_size * 0.28) + 3,
            x + round(pointer_width * 0.28) + 2,
            y + pointer_height + round(frame.cursor_size * 0.38) + 3,
            x + round(pointer_width * 0.08) + 2,
            y + round(pointer_height * 0.68) + 3,
        ]
        body = [
            x,
            y,
            x,
            y + pointer_height,
            x + pointer_width,
            y + round(pointer_height * 0.66),
            x + round(pointer_width * 0.52),
            y + round(pointer_height * 0.54),
            x + round(pointer_width * 0.72),
            y + pointer_height + round(frame.cursor_size * 0.28),
            x + round(pointer_width * 0.28),
            y + pointer_height + round(frame.cursor_size * 0.38),
            x + round(pointer_width * 0.08),
            y + round(pointer_height * 0.68),
        ]
        accent = [
            x + round(pointer_width * 0.18),
            y + round(pointer_height * 0.24),
            x + round(pointer_width * 0.18),
            y + round(pointer_height * 0.82),
            x + round(pointer_width * 0.54),
            y + round(pointer_height * 0.62),
        ]
        canvas.create_polygon(shadow, fill=self._blend("#020617", self._bg, 0.2), outline="")
        canvas.create_polygon(body, fill="#f8fafc", outline=frame.cursor_color, width=3 if frame.pressed else 2, joinstyle="round")
        canvas.create_polygon(accent, fill=self._blend(frame.cursor_color, "#ffffff", 0.35), outline="")
        glow_radius = radius + (10 if frame.pressed else 6)
        canvas.create_oval(x - glow_radius, y - glow_radius, x + glow_radius, y + glow_radius, outline=self._blend(frame.cursor_color, self._bg, 0.5), width=2)
        badge_text = frame.status_text[:24]
        badge_w = max(120, 14 + len(badge_text) * 8)
        canvas.create_rectangle(24, 24, 24 + badge_w, 54, fill="#08111f", outline=self._blend(frame.cursor_color, "#ffffff", 0.2), width=1)
        canvas.create_text(36, 39, text=badge_text, fill="#f8fafc", anchor="w", font=("Segoe UI", 11, "bold"))

    def _virtual_screen_geometry(self) -> tuple[int, int, int, int]:
        user32 = ctypes.windll.user32
        left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        return left, top, max(1, width), max(1, height)

    def _make_click_through(self, root: tk.Tk) -> None:
        try:
            hwnd = wintypes.HWND(root.winfo_id())
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            color_key = self._colorref(self._bg)
            user32.SetLayeredWindowAttributes(hwnd, ctypes.c_uint(color_key), 0, LWA_COLORKEY)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
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
        value = color.lstrip("#")
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
        return red | (green << 8) | (blue << 16)
