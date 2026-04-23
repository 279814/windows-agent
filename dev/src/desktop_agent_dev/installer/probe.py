from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import platform
import sys


@dataclass(slots=True)
class ProbeResult:
    ok: bool
    python_version: str
    platform: str
    windows_mcp_root: str | None
    checks: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def run_probe(windows_mcp_root: str | Path | None = None) -> ProbeResult:
    root = Path(windows_mcp_root) if windows_mcp_root else None
    checks = {
        "python_supported": sys.version_info >= (3, 13),
        "is_windows": sys.platform.startswith("win"),
        "windows_mcp_root_exists": bool(root and root.exists()),
    }
    notes: list[str] = []
    if not checks["python_supported"]:
        notes.append("Python 3.13+ is required.")
    if not checks["is_windows"]:
        notes.append("Windows desktop automation requires Windows.")
    if root is not None and not root.exists():
        notes.append(f"Configured Windows-MCP root does not exist: {root}")
    return ProbeResult(
        ok=all(checks.values()) if root is not None else checks["python_supported"] and checks["is_windows"],
        python_version=platform.python_version(),
        platform=platform.platform(),
        windows_mcp_root=str(root) if root is not None else None,
        checks=checks,
        notes=notes,
    )
