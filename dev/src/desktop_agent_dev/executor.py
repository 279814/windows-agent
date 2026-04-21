from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ExecutorError(RuntimeError):
    pass


@dataclass(slots=True)
class InputResult:
    action: str
    ok: bool
    detail: str
    payload: dict[str, Any] | None = None
    tool: str | None = None


class Executor:
    """Desktop execution facade with real Windows-MCP backend support."""

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    def _result(self, action: str, detail: str, ok: bool = True, payload: dict[str, Any] | None = None, tool: str | None = None) -> InputResult:
        return InputResult(action=action, ok=ok, detail=detail, payload=payload, tool=tool or action)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> InputResult:
        if self._backend is None:
            return self._result("click", f"clicked:{x},{y}:{button}:{clicks}", tool="input_click")

        if hasattr(self._backend, "click"):
            self._backend.click((x, y), button=button, clicks=clicks)
            return self._result("click", f"clicked:{x},{y}:{button}:{clicks}", tool="input_click")

        raise ExecutorError("Backend does not expose click().")

    def move(self, x: int, y: int) -> InputResult:
        if self._backend is None:
            return self._result("move", f"moved:{x},{y}", tool="input_move")

        if hasattr(self._backend, "move"):
            self._backend.move((x, y))
            return self._result("move", f"moved:{x},{y}", tool="input_move")

        raise ExecutorError("Backend does not expose move().")

    def drag(self, start: tuple[int, int], end: tuple[int, int]) -> InputResult:
        if self._backend is None:
            return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", tool="input_drag")

        if hasattr(self._backend, "move") and hasattr(self._backend, "drag"):
            self._backend.move(start)
            self._backend.drag(end)
            return self._result("drag", f"dragged:{start[0]},{start[1]}->{end[0]},{end[1]}", tool="input_drag")

        raise ExecutorError("Backend does not expose drag support.")

    def type_text(
        self,
        text: str,
        press_enter: bool = False,
        clear: bool = False,
        caret_position: str = "idle",
    ) -> InputResult:
        if self._backend is None:
            suffix = ":enter" if press_enter else ""
            return self._result("type", f"typed:{text}{suffix}", tool="input_type")

        if hasattr(self._backend, "type"):
            self._backend.type(
                (0, 0),
                text=text,
                press_enter=press_enter,
                clear=clear,
                caret_position=caret_position,
            )
            suffix = ":enter" if press_enter else ""
            return self._result("type", f"typed:{text}{suffix}", tool="input_type")

        raise ExecutorError("Backend does not expose type().")

    def multi_select(self, coordinates: list[tuple[int, int]], press_ctrl: bool = False) -> InputResult:
        if self._backend is None:
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload={"count": len(coordinates), "press_ctrl": press_ctrl},
                tool="input_multi_select",
            )

        if hasattr(self._backend, "multi_select"):
            self._backend.multi_select(press_ctrl=press_ctrl, locs=coordinates)
            return self._result(
                "multi_select",
                f"multi_selected:{len(coordinates)}:{'ctrl' if press_ctrl else 'plain'}",
                payload={"count": len(coordinates), "press_ctrl": press_ctrl},
                tool="input_multi_select",
            )

        raise ExecutorError("Backend does not expose multi_select().")

    def multi_edit(self, edits: list[tuple[int, int, str]]) -> InputResult:
        if self._backend is None:
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload={"count": len(edits)}, tool="input_multi_edit")

        if hasattr(self._backend, "multi_edit"):
            self._backend.multi_edit(edits)
            return self._result("multi_edit", f"multi_edited:{len(edits)}", payload={"count": len(edits)}, tool="input_multi_edit")

        raise ExecutorError("Backend does not expose multi_edit().")

    def shortcut(self, keys: str) -> InputResult:
        if self._backend is None:
            return self._result("shortcut", f"shortcut:{keys}", tool="input_shortcut")

        if hasattr(self._backend, "shortcut"):
            self._backend.shortcut(keys)
            return self._result("shortcut", f"shortcut:{keys}", tool="input_shortcut")

        raise ExecutorError("Backend does not expose shortcut().")

    def scroll(self, direction: str, amount: int = 1) -> InputResult:
        if self._backend is None:
            return self._result("scroll", f"scrolled:{direction}:{amount}", tool="input_scroll")

        if hasattr(self._backend, "scroll"):
            self._backend.scroll(direction=direction, wheel_times=amount)
            return self._result("scroll", f"scrolled:{direction}:{amount}", tool="input_scroll")

        raise ExecutorError("Backend does not expose scroll().")

    def launch_app(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_launch", f"launch:{name}", tool="window_launch")

        if hasattr(self._backend, "launch_app"):
            response = self._backend.launch_app(name)
            return self._result("window_launch", str(response), tool="window_launch")

        raise ExecutorError("Backend does not expose launch_app().")

    def switch_window(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_switch", f"switch:{name}", tool="window_switch")

        if hasattr(self._backend, "switch_app"):
            response = self._backend.switch_app(name)
            return self._result("window_switch", str(response), tool="window_switch")

        raise ExecutorError("Backend does not expose switch_app().")

    def focus_window(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_focus", f"focus:{name}", tool="window_focus")

        if hasattr(self._backend, "focus_app"):
            response = self._backend.focus_app(name)
            return self._result("window_focus", str(response), tool="window_focus")

        return self.switch_window(name)

    def close_window(self, name: str) -> InputResult:
        if self._backend is None:
            return self._result("window_close", f"close:{name}", tool="window_close")

        if hasattr(self._backend, "close_app"):
            response = self._backend.close_app(name)
            return self._result("window_close", str(response), tool="window_close")

        raise ExecutorError("Backend does not expose close_app().")

    def resize_window(
        self,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> InputResult:
        if self._backend is None:
            return self._result(
                "window_resize",
                f"resize:{name or 'active'}:{width}x{height}@{x},{y}",
                payload={"name": name, "width": width, "height": height, "x": x, "y": y},
                tool="window_resize",
            )

        if hasattr(self._backend, "resize_app"):
            loc = (x, y) if x is not None and y is not None else None
            size = (width, height) if width is not None and height is not None else None
            response = self._backend.resize_app(name=name, size=size, loc=loc)
            return self._result(
                "window_resize",
                str(response),
                payload={"name": name, "width": width, "height": height, "x": x, "y": y},
                tool="window_resize",
            )

        raise ExecutorError("Backend does not expose resize_app().")

    def minimize_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_minimize", f"minimize:{name or 'active'}", tool="window_minimize")
        if hasattr(self._backend, "minimize_app"):
            response = self._backend.minimize_app(name=name)
            return self._result("window_minimize", str(response), tool="window_minimize")
        raise ExecutorError("Backend does not expose minimize_app().")

    def maximize_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_maximize", f"maximize:{name or 'active'}", tool="window_maximize")
        if hasattr(self._backend, "maximize_app"):
            response = self._backend.maximize_app(name=name)
            return self._result("window_maximize", str(response), tool="window_maximize")
        raise ExecutorError("Backend does not expose maximize_app().")

    def restore_window(self, name: str | None = None) -> InputResult:
        if self._backend is None:
            return self._result("window_restore", f"restore:{name or 'active'}", tool="window_restore")
        if hasattr(self._backend, "restore_app"):
            response = self._backend.restore_app(name=name)
            return self._result("window_restore", str(response), tool="window_restore")
        raise ExecutorError("Backend does not expose restore_app().")
