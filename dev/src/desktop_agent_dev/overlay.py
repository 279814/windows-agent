from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OverlayFrame:
    visible: bool = True
    cursor_x: int = 0
    cursor_y: int = 0
    cursor_color: str = "#ff0000"
    user_cursor_color: str = "#3b82f6"
    cursor_size: int = 28
    user_cursor_size: int = 14
    persistent: bool = True
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
    transition_state: str = "idle"
    transition_reason: str | None = None
    interruption_state: str | None = None
    last_target: dict[str, int] | None = None
    last_error: str | None = None
    last_verified_at: str | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)


class OverlayRenderer:
    """In-memory overlay state holder for the virtual mouse."""

    def __init__(self) -> None:
        self.frame = OverlayFrame()
        self.frame.metadata.update(
            {
                "cursor_color": self.frame.cursor_color,
                "user_cursor_color": self.frame.user_cursor_color,
                "cursor_size": self.frame.cursor_size,
                "user_cursor_size": self.frame.user_cursor_size,
                "persistent": self.frame.persistent,
            }
        )

    def show(self) -> None:
        self.frame.visible = True

    def hide(self) -> None:
        if not self.frame.persistent:
            self.frame.visible = False

    def set_display_context(self, *, display_id: str | None = None, scale_factor: float = 1.0, monitor_bounds: list[dict[str, int]] | None = None) -> None:
        self.frame.display_id = display_id
        self.frame.scale_factor = float(scale_factor)
        self.frame.monitor_bounds = [] if monitor_bounds is None else [dict(bounds) for bounds in monitor_bounds]
        self.frame.metadata.update({"display_id": display_id, "scale_factor": self.frame.scale_factor, "monitor_bounds": self.frame.monitor_bounds, "cursor_color": self.frame.cursor_color, "user_cursor_color": self.frame.user_cursor_color})

    def update_cursor(self, x: int, y: int) -> None:
        self.frame.cursor_x = x
        self.frame.cursor_y = y
        self.frame.trail.append((x, y))
        if len(self.frame.trail) > 128:
            self.frame.trail = self.frame.trail[-128:]
        self.frame.metadata.update({"cursor_x": x, "cursor_y": y, "cursor_color": self.frame.cursor_color, "user_cursor_color": self.frame.user_cursor_color})

    def set_style(
        self,
        *,
        cursor_color: str | None = None,
        user_cursor_color: str | None = None,
        cursor_size: int | None = None,
        user_cursor_size: int | None = None,
        persistent: bool | None = None,
    ) -> None:
        if cursor_color:
            self.frame.cursor_color = str(cursor_color)
        if user_cursor_color:
            self.frame.user_cursor_color = str(user_cursor_color)
        if cursor_size is not None:
            self.frame.cursor_size = max(8, int(cursor_size))
        if user_cursor_size is not None:
            self.frame.user_cursor_size = max(4, int(user_cursor_size))
        if persistent is not None:
            self.frame.persistent = bool(persistent)
            if self.frame.persistent:
                self.frame.visible = True
        self.frame.metadata.update(
            {
                "cursor_color": self.frame.cursor_color,
                "user_cursor_color": self.frame.user_cursor_color,
                "cursor_size": self.frame.cursor_size,
                "user_cursor_size": self.frame.user_cursor_size,
                "persistent": self.frame.persistent,
            }
        )

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

    def set_transition_state(self, state: str, *, reason: str | None = None) -> None:
        self.frame.transition_state = state
        self.frame.transition_reason = reason
        self.frame.metadata.update({"transition_state": state, "transition_reason": reason})

    def set_interruption_state(self, state: str | None, *, reason: str | None = None) -> None:
        self.frame.interruption_state = state
        self.frame.metadata.update({"interruption_state": state, "interruption_reason": reason})
        if state is None:
            self.frame.metadata.pop("interruption_reason", None)

    def attach_motion(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
        self.frame.visible = True
        self.frame.last_action_status = phase
        self.record_timeline("motion", {"phase": phase, **({} if metadata is None else metadata)})
        self.frame.metadata.update({"motion_phase": phase})
        if metadata:
            self.frame.metadata.update(metadata)
            if "kind" in metadata:
                self.frame.last_action_kind = str(metadata["kind"])
            if "transition_state" in metadata:
                self.set_transition_state(str(metadata["transition_state"]), reason=None if metadata.get("transition_reason") is None else str(metadata.get("transition_reason")))
            if "transition_reason" in metadata:
                self.frame.transition_reason = None if metadata["transition_reason"] is None else str(metadata["transition_reason"])
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
            cursor_color=self.frame.cursor_color,
            user_cursor_color=self.frame.user_cursor_color,
            cursor_size=self.frame.cursor_size,
            user_cursor_size=self.frame.user_cursor_size,
            persistent=self.frame.persistent,
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
            transition_state=self.frame.transition_state,
            transition_reason=self.frame.transition_reason,
            interruption_state=self.frame.interruption_state,
            last_target=None if self.frame.last_target is None else dict(self.frame.last_target),
            last_error=self.frame.last_error,
            last_verified_at=self.frame.last_verified_at,
            timeline=[dict(item) for item in self.frame.timeline],
        )
