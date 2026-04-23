from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from os import environ

from mcp.server.fastmcp import FastMCP

from .backend_windows_mcp import BackendLoadError, build_backend_bundle
from .executor import Executor
from .manifest import build_capabilities, build_catalog, build_manifest, build_readme, build_security, build_tool_handbook
from .perception import Perception
from .planner import Planner
from .safety import SafetyGate
from .state import TaskStore
from .tool_registry import register_tool_specs


@dataclass(slots=True)
class AppServices:
    perception: Perception
    executor: Executor
    planner: Planner
    safety: SafetyGate
    task_store: TaskStore | None = None


class DesktopMCPServer:
    def __init__(self, windows_mcp_root: str | Path | None = None) -> None:
        if windows_mcp_root is None:
            windows_mcp_root = environ.get("WINDOWS_MCP_ROOT") or environ.get("WINDOWS_MCP_WORKSPACE")
        self._windows_mcp_root = Path(windows_mcp_root) if windows_mcp_root else None
        self._backend_bundle = None
        if self._windows_mcp_root is not None:
            try:
                self._backend_bundle = build_backend_bundle(self._windows_mcp_root)
            except BackendLoadError:
                self._backend_bundle = None
        backend = self._backend_bundle.desktop if self._backend_bundle else None
        self.services = AppServices(
            perception=Perception(backend=backend),
            executor=Executor(backend=backend),
            planner=Planner(),
            safety=SafetyGate(),
            task_store=TaskStore(),
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
            resource_payloads = {
                "desktop-agent-dev://manifest": self.manifest,
                "desktop-agent-dev://readme": self.readme,
                "desktop-agent-dev://catalog": self.catalog,
                "desktop-agent-dev://capabilities": self.capabilities,
                "desktop-agent-dev://security": self.security,
                "desktop-agent-dev://tool-handbook": self.tool_handbook,
                "desktop-agent-dev://tool-index": self.tool_registry.metadata(),
            }
            for resource in self.tool_registry.resource_index():
                uri = resource["uri"]
                name = uri.split("://", 1)[1]
                payload = resource_payloads[uri]

                def _resource_handler():
                    return payload

                self.mcp.resource(name=name, uri=uri, description=resource["description"])(_resource_handler)

    def run(self) -> None:
        self.mcp.run()


def create_server(windows_mcp_root: str | Path | None = None) -> DesktopMCPServer:
    return DesktopMCPServer(windows_mcp_root=windows_mcp_root)
