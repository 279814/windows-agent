from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastmcp import FastMCP

from .backend_windows_mcp import build_backend_bundle
from .executor import Executor
from .perception import Perception
from .planner import Planner
from .safety import SafetyGate
from .tool_registry import register_tool_specs


@dataclass(slots=True)
class AppServices:
    perception: Perception
    executor: Executor
    planner: Planner
    safety: SafetyGate


class DesktopMCPServer:
    def __init__(self, windows_mcp_root: str | Path | None = None) -> None:
        self._windows_mcp_root = Path(windows_mcp_root) if windows_mcp_root else None
        self._backend_bundle = None
        if self._windows_mcp_root is not None:
            self._backend_bundle = build_backend_bundle(self._windows_mcp_root)
        backend = self._backend_bundle.desktop if self._backend_bundle else None
        self.services = AppServices(
            perception=Perception(backend=backend),
            executor=Executor(backend=backend),
            planner=Planner(),
            safety=SafetyGate(),
        )
        self.mcp = FastMCP("desktop-agent-dev")
        register_tool_specs(self)

    def run(self) -> None:
        self.mcp.run()


def create_server(windows_mcp_root: str | Path | None = None) -> DesktopMCPServer:
    return DesktopMCPServer(windows_mcp_root=windows_mcp_root)
