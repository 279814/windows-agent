"""App tool — launch, resize, switch, minimize applications."""

from typing import Any, Literal

from mcp.types import ToolAnnotations
from windows_mcp.analytics import with_analytics
from fastmcp import Context


def _result(tool: str, mode: str, ok: bool, message: str, *, name: str | None, response: str, status: int, pid: int) -> dict[str, Any]:
    return {
        "ok": ok,
        "tool": tool,
        "message": message,
        "data": {
            "mode": mode,
            "name": name,
            "response": response,
            "status": status,
            "pid": pid,
            "outcome": "success" if ok else "failed",
        },
        "error": None if ok else {
            "code": "capability_missing" if "not implemented" in response.lower() or "not supported" in response.lower() else "operation_failed",
            "message": response,
        },
    }


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="App",
        description="Open/start/launch applications and manage windows. Keywords: open, start, launch, program, application, window, foreground, focus, resize, minimize. Modes: 'launch' (opens the prescribed application), 'resize' (adjusts the size/position of a named window or the active window if name is omitted), 'switch' (brings a specific window into focus), 'minimize' (minimizes a named or active window).",
        annotations=ToolAnnotations(
            title="App",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "App-Tool")
    def app_tool(
        mode: Literal['launch', 'resize', 'switch', 'minimize'] = 'launch',
        name: str | None = None,
        window_loc: list[int] | None = None,
        window_size: list[int] | None = None,
        ctx: Context = None,
    ):
        response = get_desktop().app(mode, name, window_loc, window_size)
        if isinstance(response, tuple) and len(response) == 3:
            message, status, pid = response
        else:
            message, status, pid = str(response), 1, 0

        ok = status == 0
        return _result(
            tool="App",
            mode=mode,
            ok=ok,
            message=message if ok else f"{mode} failed",
            name=name,
            response=message,
            status=status,
            pid=pid,
        )
