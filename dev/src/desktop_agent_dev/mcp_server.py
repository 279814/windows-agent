from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:  # pragma: no cover - optional dependency in dev/test environments
    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str, instructions: str | None = None, lifespan: Any | None = None) -> None:
            self.name = name
            self.instructions = instructions
            self.lifespan = lifespan
            self._tools: list[Callable[..., Any]] = []
            self._resources: list[dict[str, Any]] = []

        def tool(self, name: str | None = None, description: str | None = None):
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._tools.append(fn)
                return fn

            return decorator

        def resource(self, name: str | None = None, uri: str | None = None, description: str | None = None):
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._resources.append({"name": name, "uri": uri, "description": description, "fn": fn})
                return fn

            return decorator

        def run(self) -> None:
            return None

from .backend_windows_mcp import build_backend_bundle
from .executor import Executor
from .manifest import build_capabilities, build_catalog, build_manifest, build_readme, build_security, build_tool_handbook
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
        self.readme = build_readme(self.tool_registry)
        self.catalog = build_catalog(self.tool_registry)
        self.capabilities = build_capabilities(self.tool_registry)
        self.security = build_security(self.tool_registry)
        self.manifest = build_manifest(self.tool_registry)
        self.tool_handbook = build_tool_handbook(self.tool_registry)
        self._register_resources()

    def _register_resources(self) -> None:
        if hasattr(self.mcp, "resource"):
            self.mcp.resource(name="readme", uri="desktop-agent-dev://readme", description="Project overview and usage guidance.")(lambda: self.readme)
            self.mcp.resource(name="catalog", uri="desktop-agent-dev://catalog", description="Grouped tool catalog with detailed metadata.")(lambda: self.catalog)
            self.mcp.resource(name="capabilities", uri="desktop-agent-dev://capabilities", description="Capability matrix and client hints.")(lambda: self.capabilities)
            self.mcp.resource(name="security", uri="desktop-agent-dev://security", description="Permission model and risk policy.")(lambda: self.security)
            self.mcp.resource(name="manifest", uri="desktop-agent-dev://manifest", description="MCP document manifest for the desktop agent.")(lambda: self.manifest)
            self.mcp.resource(name="tool-handbook", uri="desktop-agent-dev://tool-handbook", description="Client-readable tool handbook for Cursor/Claude catalogs.")(lambda: self.tool_handbook)
            self.mcp.resource(name="tool-index", uri="desktop-agent-dev://tool-index", description="Tool catalog index with grouped metadata.")(lambda: self.tool_registry.metadata())

    def run(self) -> None:
        self.mcp.run()


def create_server(windows_mcp_root: str | Path | None = None) -> DesktopMCPServer:
    return DesktopMCPServer(windows_mcp_root=windows_mcp_root)
