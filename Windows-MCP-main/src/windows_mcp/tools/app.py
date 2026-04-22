"""App tool — launch, resize, switch, minimize applications."""

from typing import Any, Literal

from mcp.types import ToolAnnotations
from windows_mcp.analytics import with_analytics
from windows_mcp.errors import (
    APP_ERROR_CAPABILITY_MISSING,
    APP_ERROR_NOT_FOUND,
    APP_ERROR_OPERATION_FAILED,
    APP_ERROR_VERIFICATION_TIMEOUT,
)
from fastmcp import Context


def _classify_app_error(response: str) -> str:
    lowered = response.lower()
    if "not implemented" in lowered or "not supported" in lowered or "capability" in lowered:
        return APP_ERROR_CAPABILITY_MISSING
    if "not found" in lowered or "no windows found" in lowered or ("application" in lowered and "not found" in lowered):
        return APP_ERROR_NOT_FOUND
    if "not detected yet" in lowered:
        return APP_ERROR_VERIFICATION_TIMEOUT
    return APP_ERROR_OPERATION_FAILED


def _result(tool: str, mode: str, ok: bool, message: str, *, name: str | None, response: str, status: int, pid: int, verified: bool = False, verification_source: str | None = None) -> dict[str, Any]:
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
            "verified": verified,
            "verification_source": verification_source,
            "outcome": "success" if ok else "failed",
        },
        "error": None if ok else {
            "code": _classify_app_error(response),
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
        if isinstance(response, dict):
            data = response.get("data", {}) or {}
            error = response.get("error")
            return {
                "ok": bool(response.get("ok")),
                "tool": response.get("tool", "App"),
                "message": response.get("message", ""),
                "data": data,
                "error": error,
            }

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
            verified=False,
            verification_source=None,
        )
