from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict


ToolName = Literal[
    "desktop_snapshot",
    "input_click",
    "input_move",
    "input_drag",
    "input_type",
    "input_multi_select",
    "input_multi_edit",
    "input_shortcut",
    "input_scroll",
    "input_launch_app",
    "window_launch",
    "window_switch",
    "window_focus",
    "window_close",
    "window_resize",
    "window_minimize",
    "window_maximize",
    "window_restore",
    "task_plan",
    "task_state",
]


@dataclass(slots=True)
class ToolResponse:
    ok: bool
    tool: str
    message: str | None = None
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"ok": self.ok, "tool": self.tool}
        if self.message is not None:
            payload["message"] = self.message
        if self.data is not None:
            payload["data"] = self.data
        if self.error is not None:
            payload["error"] = self.error
        return payload


class Point(TypedDict):
    x: int
    y: int


class MultiSelectParams(TypedDict):
    coordinates: list[Point]
    press_ctrl: bool


class MultiEditItem(TypedDict):
    x: int
    y: int
    text: str


class MultiEditParams(TypedDict):
    edits: list[MultiEditItem]


class WindowResizeParams(TypedDict, total=False):
    name: str
    width: int
    height: int
    x: int
    y: int


class WindowLifecycleParams(TypedDict, total=False):
    name: str


class InputEnvelope(TypedDict, total=False):
    action: str
    ok: bool
    detail: str
    payload: dict[str, Any]


def ok(tool: ToolName | str, data: dict[str, Any], message: str = "ok") -> dict[str, Any]:
    return ToolResponse(ok=True, tool=tool, message=message, data=data).as_dict()


def error(tool: ToolName | str, message: str, code: str = "blocked") -> dict[str, Any]:
    return ToolResponse(ok=False, tool=tool, error={"code": code, "message": message}).as_dict()


def input_payload(action: str, ok_flag: bool, detail: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"action": action, "ok": ok_flag, "detail": detail, "payload": payload or {}}
