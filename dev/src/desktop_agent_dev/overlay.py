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
    last_action_kind: str | None = None
    last_action_status: str | None = None
    last_target: dict[str, int] | None = None
    last_error: str | None = None
    last_verified_at: str | None = None


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

    def attach_motion(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
        self.frame.visible = True
        self.frame.last_action_status = phase
        self.frame.metadata.update({"motion_phase": phase})
        if metadata:
            self.frame.metadata.update(metadata)
            if "kind" in metadata:
                self.frame.last_action_kind = str(metadata["kind"])
            if "last_target" in metadata and isinstance(metadata["last_target"], dict):
                self.frame.last_target = {"x": int(metadata["last_target"].get("x", 0)), "y": int(metadata["last_target"].get("y", 0))}
            if "last_error" in metadata:
                self.frame.last_error = None if metadata["last_error"] is None else str(metadata["last_error"])
            if "last_verified_at" in metadata:
                self.frame.last_verified_at = None if metadata["last_verified_at"] is None else str(metadata["last_verified_at"])

    def snapshot(self) -> OverlayFrame:
        return OverlayFrame(
            visible=self.frame.visible,
            cursor_x=self.frame.cursor_x,
            cursor_y=self.frame.cursor_y,
            trail=list(self.frame.trail),
            metadata=dict(self.frame.metadata),
            last_action_kind=self.frame.last_action_kind,
            last_action_status=self.frame.last_action_status,
            last_target=None if self.frame.last_target is None else dict(self.frame.last_target),
            last_error=self.frame.last_error,
            last_verified_at=self.frame.last_verified_at,
        )
