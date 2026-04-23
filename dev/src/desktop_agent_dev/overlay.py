from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OverlayFrame:
    visible: bool = False
    cursor_x: int = 0
    cursor_y: int = 0
    trail: list[tuple[int, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OverlayRenderer:
    """First-pass dev overlay state holder."""

    def __init__(self) -> None:
        self.frame = OverlayFrame()

    def show(self) -> None:
        self.frame.visible = True

    def hide(self) -> None:
        self.frame.visible = False

    def update_cursor(self, x: int, y: int) -> None:
        self.frame.cursor_x = x
        self.frame.cursor_y = y
        self.frame.trail.append((x, y))
        if len(self.frame.trail) > 128:
            self.frame.trail = self.frame.trail[-128:]

    def snapshot(self) -> OverlayFrame:
        return OverlayFrame(
            visible=self.frame.visible,
            cursor_x=self.frame.cursor_x,
            cursor_y=self.frame.cursor_y,
            trail=list(self.frame.trail),
            metadata=dict(self.frame.metadata),
        )
