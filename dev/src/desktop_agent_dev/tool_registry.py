from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

ToolKind = Literal["snapshot", "input", "window", "task"]

TOOL_GROUP_TITLES = {
    "snapshot": "Snapshot & Perception",
    "input": "Input & Action",
    "window": "Window Management",
    "task": "Task Orchestration",
}


@dataclass(slots=True)
class ToolSpec:
    name: str
    kind: ToolKind
    params_schema: dict[str, Any]
    result_schema: dict[str, Any]
    permission: str | None
    executor: Callable[..., dict[str, Any]]
    description: str = ""
    param_description: str = ""
    result_description: str = ""
    input_examples: list[dict[str, Any]] | None = None
    output_examples: list[dict[str, Any]] | None = None
    safety_notes: str = ""
    implementation_notes: str = ""


@dataclass(slots=True)
class ToolRegistry:
    specs: dict[str, ToolSpec]

    def register(self, spec: ToolSpec) -> None:
        self.specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self.specs[name]

    def resource_index(self) -> list[dict[str, str]]:
        return [
            {"uri": "desktop-agent-dev://readme", "title": "README", "description": "Project overview and usage guidance."},
            {"uri": "desktop-agent-dev://catalog", "title": "Catalog", "description": "Grouped tool directory with detailed metadata."},
            {"uri": "desktop-agent-dev://capabilities", "title": "Capabilities", "description": "Capability matrix and client hints."},
            {"uri": "desktop-agent-dev://security", "title": "Security", "description": "Permission model and risk policy."},
            {"uri": "desktop-agent-dev://tool-handbook", "title": "Tool Handbook", "description": "Formal directory for MCP clients and agents."},
            {"uri": "desktop-agent-dev://tool-index", "title": "Tool Index", "description": "Normalized tool metadata for clients."},
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "version": "1.5",
            "stage": "phase1",
            "tool_catalog": self.tool_catalog(),
            "group_catalog": self.group_catalog(),
            "resource_index": self.resource_index(),
            "capabilities": self.capabilities(),
            "policy": self.policy(),
            "examples": self.examples(),
            "summary": "Windows-compatible desktop agent tools for observation, input, window control, and task planning.",
        }

    def tool_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "kind": spec.kind,
                "title": spec.name.replace("_", " ").title(),
                "description": spec.description,
                "param_description": spec.param_description,
                "result_description": spec.result_description,
                "permission": spec.permission,
                "parameters": spec.params_schema,
                "result": spec.result_schema,
                "input_examples": spec.input_examples or [],
                "output_examples": spec.output_examples or [],
                "safety_notes": spec.safety_notes,
                "implementation_notes": spec.implementation_notes,
            }
            for spec in self.specs.values()
        ]

    def group_catalog(self) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        order = ["snapshot", "input", "window", "task"]
        for spec in self.specs.values():
            group = grouped.setdefault(
                spec.kind,
                {"kind": spec.kind, "title": TOOL_GROUP_TITLES.get(spec.kind, spec.kind.title()), "tools": []},
            )
            group["tools"].append(spec.name)
        return [grouped[kind] for kind in order if kind in grouped] + [group for kind, group in grouped.items() if kind not in order]

    def capabilities(self) -> dict[str, Any]:
        return {
            "snapshot": True,
            "input": True,
            "window": True,
            "task": True,
            "ocr_hooks": True,
            "vision_hooks": True,
            "supports_handshake_metadata": True,
        }

    def policy(self) -> dict[str, Any]:
        return {
            "default_mode": "observe-first",
            "permission_model": "per-tool",
            "risk_levels": {
                "snapshot": "low",
                "input": "medium",
                "window": "medium",
                "task": "low",
            },
            "high_risk_actions": ["window_close", "launch_app"],
            "notes": [
                "High-risk actions remain gated by the safety service.",
                "Tool metadata is normalized for MCP client catalogs and handbooks.",
            ],
        }

    def examples(self) -> list[dict[str, Any]]:
        return [
            {
                "tool": spec.name,
                "input_examples": spec.input_examples or [],
                "output_examples": spec.output_examples or [],
            }
            for spec in self.specs.values()
        ]


RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "default": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "tool": {"type": "string"},
            "message": {"type": "string"},
            "data": {"type": "object"},
            "error": {"type": "object"},
        },
        "required": ["ok", "tool"],
    },
    "input": {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "ok": {"type": "boolean"},
            "detail": {"type": "string"},
            "payload": {"type": "object"},
        },
        "required": ["action", "ok", "detail", "payload"],
    },
}


def build_registry() -> ToolRegistry:
    return ToolRegistry(specs={})


def register_tool_specs(server: Any) -> ToolRegistry:
    from .tool_specs import register_desktop_tools, register_input_tools, register_task_tools, register_vision_tools, register_window_tools

    registry = build_registry()
    register_desktop_tools(registry, server.services)
    register_input_tools(registry, server.services)
    register_window_tools(registry, server.services)
    register_task_tools(registry, server.services)
    register_vision_tools(registry, server.services)

    for spec in registry.specs.values():
        spec.executor.__doc__ = spec.description or spec.name.replace("_", " ")
        spec.executor.__name__ = spec.name
        server.mcp.tool()(spec.executor)

    server.tool_registry = registry
    return registry
