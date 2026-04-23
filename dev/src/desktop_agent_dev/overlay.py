from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OverlayFrame:
    visible: bool = False
    cursor_x: int = 0
    cursor_y: int = 0
    trail: list[tuple[int, int]] = field(default_factory=list)
    click_ripples: list[dict[str, int]] = field(default_factory=list)
    drag_active: bool = False
    drag_start: dict[str, int] | None = None
    display_id: str | None = None
    scale_factor: float = 1.0
    monitor_bounds: list[dict[str, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_action_kind: str | None = None
    last_action_status: str | None = None
    last_target: dict[str, int] | None = None
    last_error: str | None = None
    last_verified_at: str | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)


class OverlayRenderer:
    """In-memory overlay state holder for the virtual mouse."""

    def __init__(self) -> None:
        self.frame = OverlayFrame()

    def show(self) -> None:
        self.frame.visible = True

    def hide(self) -> None:
        self.frame.visible = False

    def set_display_context(self, *, display_id: str | None = None, scale_factor: float = 1.0, monitor_bounds: list[dict[str, int]] | None = None) -> None:
        self.frame.display_id = display_id
        self.frame.scale_factor = float(scale_factor)
        self.frame.monitor_bounds = [] if monitor_bounds is None else [dict(bounds) for bounds in monitor_bounds]
        self.frame.metadata.update({"display_id": display_id, "scale_factor": self.frame.scale_factor, "monitor_bounds": self.frame.monitor_bounds})

    def update_cursor(self, x: int, y: int) -> None:
        self.frame.cursor_x = x
        self.frame.cursor_y = y
        self.frame.trail.append((x, y))
        if len(self.frame.trail) > 128:
            self.frame.trail = self.frame.trail[-128:]

    def draw_click_ripple(self, x: int, y: int, radius: int = 18) -> None:
        self.frame.click_ripples.append({"x": x, "y": y, "radius": radius})
        if len(self.frame.click_ripples) > 16:
            self.frame.click_ripples = self.frame.click_ripples[-16:]
        self.frame.metadata["click_ripple_count"] = len(self.frame.click_ripples)

    def set_drag_state(self, active: bool, *, start: dict[str, int] | None = None) -> None:
        self.frame.drag_active = active
        self.frame.drag_start = None if start is None else {"x": int(start.get("x", 0)), "y": int(start.get("y", 0))}
        self.frame.metadata.update({"drag_active": active, "drag_start": self.frame.drag_start})

    def record_timeline(self, event: str, metadata: dict[str, Any] | None = None) -> None:
        item = {
            "event": event,
            "at": None,
            "phase": None,
            "kind": None,
            "data": {},
        }
        if metadata:
            item.update({k: v for k, v in metadata.items() if k in {"at", "phase", "kind"}})
            item["data"] = {k: v for k, v in metadata.items() if k not in {"at", "phase", "kind"}}
        self.frame.timeline.append(item)
        if len(self.frame.timeline) > 64:
            self.frame.timeline = self.frame.timeline[-64:]
        self.frame.metadata["timeline_length"] = len(self.frame.timeline)

    def attach_motion(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
        self.frame.visible = True
        self.frame.last_action_status = phase
        self.record_timeline("motion", {"phase": phase, **({} if metadata is None else metadata)})
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
            click_ripples=[dict(ripple) for ripple in self.frame.click_ripples],
            drag_active=self.frame.drag_active,
            drag_start=None if self.frame.drag_start is None else dict(self.frame.drag_start),
            display_id=self.frame.display_id,
            scale_factor=self.frame.scale_factor,
            monitor_bounds=[dict(bounds) for bounds in self.frame.monitor_bounds],
            metadata=dict(self.frame.metadata),
            last_action_kind=self.frame.last_action_kind,
            last_action_status=self.frame.last_action_status,
            last_target=None if self.frame.last_target is None else dict(self.frame.last_target),
            last_error=self.frame.last_error,
            last_verified_at=self.frame.last_verified_at,
            timeline=[dict(item) for item in self.frame.timeline],
        )
