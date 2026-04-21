from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

ToolKind = Literal["snapshot", "input", "window", "task"]


@dataclass(slots=True)
class ToolSpec:
    name: str
    kind: ToolKind
    params_schema: dict[str, Any]
    result_schema: dict[str, Any]
    permission: str | None
    executor: Callable[..., dict[str, Any]]
    description: str = ""
    examples: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class ToolRegistry:
    specs: dict[str, ToolSpec]

    def register(self, spec: ToolSpec) -> None:
        self.specs[spec.name] = spec

    def metadata(self) -> dict[str, Any]:
        return {
            "version": "1.1",
            "stage": "phase1",
            "tools": [
                {
                    "name": spec.name,
                    "kind": spec.kind,
                    "description": spec.description,
                    "permission": spec.permission,
                    "parameters": spec.params_schema,
                    "result": spec.result_schema,
                    "examples": spec.examples or [],
                }
                for spec in self.specs.values()
            ],
            "groups": self.groups(),
            "capabilities": {
                "snapshot": True,
                "input": True,
                "window": True,
                "task": True,
                "ocr_hooks": True,
                "vision_hooks": True,
            },
            "client_hints": {
                "tool_summary": True,
                "parameter_help": True,
                "execution_examples": True,
                "phase": "first-stage",
            },
        }

    def groups(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[str]] = {}
        for spec in self.specs.values():
            grouped.setdefault(spec.kind, []).append(spec.name)
        return [{"kind": kind, "tools": tools} for kind, tools in grouped.items()]


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
        server.mcp.tool()(spec.executor)

    server.tool_registry = registry
    return registry
