from __future__ import annotations

import ctypes
from ctypes import wintypes
from math import sqrt
import os


VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04


class NativeUserTakeoverMonitor:
    """Local interruption detector that does not depend on backend state."""

    def __init__(self, *, pointer_drift_threshold: int = 24) -> None:
        self._enabled = os.name == "nt"
        self._pointer_drift_threshold = pointer_drift_threshold
        self._user32 = ctypes.windll.user32 if self._enabled else None
        self._baseline: tuple[int, int] | None = None
        self._enable_pointer_drift = False

    def begin(self, *, expected_cursor: tuple[int, int] | None = None, enable_pointer_drift: bool = False) -> None:
        self._baseline = expected_cursor
        self._enable_pointer_drift = enable_pointer_drift

    def end(self) -> None:
        self._baseline = None
        self._enable_pointer_drift = False

    def reason(self, *, expected_cursor: tuple[int, int] | None = None) -> str | None:
        if not self._enabled or self._user32 is None:
            return None
        if self._pressed(VK_ESCAPE):
            return "keyboard_escape"
        if self._pressed(VK_LBUTTON) or self._pressed(VK_RBUTTON) or self._pressed(VK_MBUTTON):
            return "mouse_button"
        if self._enable_pointer_drift:
            reference = expected_cursor or self._baseline
            if reference is not None:
                actual = self._cursor_position()
                if actual is not None:
                    dx = actual[0] - reference[0]
                    dy = actual[1] - reference[1]
                    if sqrt(dx * dx + dy * dy) > self._pointer_drift_threshold:
                        return "pointer_drift"
        return None

    def is_active(self, *, expected_cursor: tuple[int, int] | None = None) -> bool:
        return self.reason(expected_cursor=expected_cursor) is not None

    def _pressed(self, vk_code: int) -> bool:
        return bool(self._user32.GetAsyncKeyState(vk_code) & 0x8000)

    def _cursor_position(self) -> tuple[int, int] | None:
        point = wintypes.POINT()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)
