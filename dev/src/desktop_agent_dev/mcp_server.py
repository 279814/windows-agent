from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from os import environ

from mcp.server.fastmcp import FastMCP

from .backend_windows_mcp import BackendLoadError, build_backend_bundle
from .executor import Executor
from .manifest import build_capabilities, build_catalog, build_manifest, build_readme, build_security, build_tool_handbook, build_tool_index
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
        self.tool_index = build_tool_index(self.tool_registry)
        self.tool_discovery = self._build_tool_discovery()
        self._register_resources()

    def _build_tool_discovery(self) -> dict[str, object]:
        tools = self.tool_registry.tool_catalog()
        groups = self.tool_registry.group_catalog()
        resources = self.tool_registry.resource_index()
        by_name = {tool["name"]: tool for tool in tools}

        def _normalize_tool(tool: dict[str, object] | None) -> dict[str, object] | None:
            if tool is None:
                return None
            return {
                "name": tool["name"],
                "kind": tool["kind"],
                "group": tool.get("group"),
                "description": tool["description"],
                "implementation_status": tool["implementation_status"],
                "verification_semantics": tool["verification_semantics"],
                "targeting_semantics": tool["targeting_semantics"],
                "discoverability": tool.get("discoverability"),
                "safety_notes": tool.get("safety_notes"),
                "param_description": tool.get("param_description"),
                "result_description": tool.get("result_description"),
                "input_examples": tool.get("input_examples", []),
                "output_examples": tool.get("output_examples", []),
                "resource_uri": tool.get("resource_uri"),
                "supports_frontend_rendering": True,
            }

        motion_tool = _normalize_tool(by_name.get("motion_preview"))
        overlay_tool = _normalize_tool(by_name.get("overlay_state"))

        render_groups = []
        for group in groups:
            render_groups.append(
                {
                    "kind": group["kind"],
                    "title": group["title"],
                    "count": len(group.get("tools", [])),
                    "tools": [
                        {
                            "name": by_name[tool_name]["name"],
                            "description": by_name[tool_name]["description"],
                            "implementation_status": by_name[tool_name]["implementation_status"],
                        }
                        for tool_name in group.get("tools", [])
                    ],
                }
            )

        return {
            "version": "1.6",
            "layout": {
                "kind": "frontend-discovery",
                "render_mode": "cards-and-sections",
                "recommended_components": ["resource-list", "group-tabs", "tool-card", "tool-detail", "status-badge", "failure-banner", "display-context-chip"],
            },
            "summary": "Compact discovery catalog for MCP clients that want to enumerate tools and quickly locate motion_preview and overlay_state, while surfacing display-context metadata, UAC-aware recovery hints, and failure fallback guidance.",
            "resources": {
                "items": [
                    {"uri": resource["uri"], "title": resource["title"], "description": resource["description"]}
                    for resource in resources
                ],
            },
            "tool_groups": render_groups,
            "tools": [
                _normalize_tool(tool) for tool in tools
            ],
            "focus_tools": {
                "motion_preview": motion_tool,
                "overlay_state": overlay_tool,
            },
            "render_hints": {
                "group_order": ["snapshot", "input", "motion", "overlay", "window", "task"],
                "primary_focus": ["motion_preview", "overlay_state"],
                "use_cards_for": ["focus_tools", "tool_groups"],
                "use_table_for": ["tools"],
            },
        }

    def _register_resources(self) -> None:
        if hasattr(self.mcp, "resource"):
            resource_payloads = {
                "desktop-agent-dev://manifest": self.manifest,
                "desktop-agent-dev://readme": self.readme,
                "desktop-agent-dev://catalog": self.catalog,
                "desktop-agent-dev://capabilities": self.capabilities,
                "desktop-agent-dev://security": self.security,
                "desktop-agent-dev://tool-handbook": self.tool_handbook,
                "desktop-agent-dev://tool-index": self.tool_index,
                "desktop-agent-dev://tool-discovery": self.tool_discovery,
            }

            def _make_resource_handler(payload: object):
                def _resource_handler():
                    return payload

                return _resource_handler

            for resource in self.tool_registry.resource_index() + [{"uri": "desktop-agent-dev://tool-discovery", "description": "Compact discovery catalog with direct focus-tool entries for motion_preview and overlay_state.", "title": "Tool Discovery"}]:
                uri = resource["uri"]
                name = uri.split("://", 1)[1]
                payload = resource_payloads[uri]
                self.mcp.resource(name=name, uri=uri, description=resource["description"])(_make_resource_handler(payload))

    def run(self) -> None:
        self.mcp.run()


def create_server(windows_mcp_root: str | Path | None = None) -> DesktopMCPServer:
    return DesktopMCPServer(windows_mcp_root=windows_mcp_root)
