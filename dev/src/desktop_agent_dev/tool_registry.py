from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal


DOC_SECTIONS = ("Best for", "Not recommended for", "Warning", "Common mistakes", "Prompt Example", "Usage Example", "Returns", "Parameters", "Safety", "Implementation")


def format_tool_doc(*, summary: str, best_for: str, not_recommended_for: str, warning: str, common_mistakes: list[str], prompt_example: str, usage_example: Any, returns: str, parameters: str, safety: str = "", implementation: str = "") -> str:
    parts = [summary, "", f"Best for: {best_for}", f"Not recommended for: {not_recommended_for}", f"Warning: {warning}", "Common mistakes:"]
    parts.extend([f"- {item}" for item in common_mistakes])
    parts.extend(["", f"Prompt Example: {prompt_example}", "Usage Example:", f"{usage_example}", "", f"Returns: {returns}", f"Parameters: {parameters}"])
    if safety:
        parts.extend([f"Safety: {safety}"])
    if implementation:
        parts.extend([f"Implementation: {implementation}"])
    return "\n".join(parts)

ToolKind = Literal["snapshot", "input", "window", "task"]

TOOL_GROUP_TITLES = {
    "snapshot": "Snapshot & Perception",
    "input": "Input & Action",
    "window": "Window Management",
    "task": "Task Orchestration",
}

TODO_PLACEHOLDER_TOOLS = ("ocr_extract", "ui_match", "vision_capture", "vision_locate")

RESOURCE_DESCRIPTIONS: dict[str, str] = {
    "desktop-agent-dev://manifest": "Machine-readable MCP manifest covering resource links, verification semantics, window handle/pid targeting, multi-source verification rules, and TODO placeholders.",
    "desktop-agent-dev://readme": "Project overview and operator guidance for desktop observation, input, window control, and task orchestration, with verification semantics and TODO placeholders.",
    "desktop-agent-dev://catalog": "Grouped tool catalog with normalized metadata, implementation status, verification semantics, targeting notes, examples, and TODO placeholders.",
    "desktop-agent-dev://capabilities": "Capability matrix, client hints, risk posture, verification affordances, and explicit TODO placeholder status.",
    "desktop-agent-dev://security": "Permission model and high-risk action policy, including verification-oriented operating guidance and placeholder caveats.",
    "desktop-agent-dev://tool-handbook": "Client-readable handbook that explains tool usage, verification semantics, handle/pid target selection, payload expectations, and TODO placeholders.",
    "desktop-agent-dev://tool-index": "Normalized tool index for MCP clients with implementation status, verification semantics, targeting semantics, result semantics, and TODO placeholders.",
}

RESOURCE_TITLES: dict[str, str] = {
    "desktop-agent-dev://manifest": "Manifest",
    "desktop-agent-dev://readme": "README",
    "desktop-agent-dev://catalog": "Catalog",
    "desktop-agent-dev://capabilities": "Capabilities",
    "desktop-agent-dev://security": "Security",
    "desktop-agent-dev://tool-handbook": "Tool Handbook",
    "desktop-agent-dev://tool-index": "Tool Index",
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
    backend_method: str = ""


@dataclass(slots=True)
class ToolRegistry:
    specs: dict[str, ToolSpec]

    def register(self, spec: ToolSpec) -> None:
        self.specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self.specs[name]

    def resource_index(self) -> list[dict[str, str]]:
        ordered_uris = (
            "desktop-agent-dev://manifest",
            "desktop-agent-dev://readme",
            "desktop-agent-dev://catalog",
            "desktop-agent-dev://capabilities",
            "desktop-agent-dev://security",
            "desktop-agent-dev://tool-handbook",
            "desktop-agent-dev://tool-index",
        )
        return [
            {
                "uri": uri,
                "title": RESOURCE_TITLES[uri],
                "description": RESOURCE_DESCRIPTIONS[uri],
            }
            for uri in ordered_uris
        ]

    def _tool_verification_semantics(self, spec: ToolSpec) -> str:
        if spec.name in TODO_PLACEHOLDER_TOOLS:
            return "TODO placeholder only. The tool intentionally returns a not_implemented-shaped response and should be routed to fallback logic until the capability lands."
        if spec.kind == "window":
            return "Top-level ok reflects the verified desktop outcome, not only backend success. Prefer handle or pid selectors when available, and inspect verified, matched_by, before_handle, after_handle, verification_mode, backend_response_detail, and backend_response_code."
        if spec.name == "input_type":
            return "Validation is explicit: inspect focused_control and validation.before/after fields to confirm the intended control changed."
        if spec.name == "input_shortcut":
            return "Verification is contextual: inspect target_window, focus_before, focus_after, focus_changed, and injection_result to confirm the shortcut landed in the intended foreground context."
        if spec.name == "input_click":
            return "Payload may include hit-test element metadata when the desktop backend can resolve the clicked surface. Treat missing or weak element metadata as partial verification and pair with desktop_snapshot when precision matters."
        if spec.name in {"input_move", "input_drag", "input_scroll", "input_multi_edit", "input_multi_select"}:
            return "The action result confirms dispatch. Payload richness currently varies by executor, so pair with desktop_snapshot or downstream state checks when you need post-action verification."
        if spec.kind == "snapshot":
            return "Read-only observations are already normalized for clients. Prefer active_window, windows, focused_control, and screenshot metadata when verifying state."
        if spec.kind == "task":
            return "Task tools return planner state rather than desktop-side effects. Verify progress through task_id, step_index, observations, and status."
        return "Use the normalized payload fields together with backend-specific detail fields when present."

    def _tool_targeting_semantics(self, spec: ToolSpec) -> str | None:
        properties = (spec.params_schema or {}).get("properties") or {}
        if {"name", "handle", "pid"}.issubset(properties):
            return "Target selection precedence is handle > pid > name. Prefer handle for duplicate titles and pid for process-level disambiguation."
        return None

    def _tool_implementation_status(self, spec: ToolSpec) -> str:
        return "todo_placeholder" if spec.name in TODO_PLACEHOLDER_TOOLS else "implemented"

    def metadata(self) -> dict[str, Any]:
        return {
            "version": "1.6",
            "stage": "phase1",
            "tool_catalog": self.tool_catalog(),
            "group_catalog": self.group_catalog(),
            "resource_index": self.resource_index(),
            "capabilities": self.capabilities(),
            "policy": self.policy(),
            "examples": self.examples(),
            "summary": "Windows desktop agent tool metadata for observation, input, window control, and task orchestration, with explicit verification semantics, handle/pid targeting guidance, multi-source window verification, and TODO placeholders.",
            "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
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
                "backend_method": spec.backend_method,
                "implementation_status": self._tool_implementation_status(spec),
                "verification_semantics": self._tool_verification_semantics(spec),
                "targeting_semantics": self._tool_targeting_semantics(spec),
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
            "ocr_hooks": False,
            "vision_hooks": False,
            "supports_handshake_metadata": True,
            "verification_semantics_documented": True,
            "handle_pid_targeting_documented": True,
            "window_multi_source_verification": True,
            "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
            "placeholder_tools_implemented": False,
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
            "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
            "notes": [
                "High-risk actions remain gated by the safety service.",
                "Tool metadata is normalized for MCP client catalogs and handbooks.",
                "Window tools support handle/pid-aware targeting and report verification-oriented payload fields for post-action auditing.",
                "Several input tools are dispatch-confirming by design; pair them with desktop_snapshot when richer post-action verification is required.",
                "TODO placeholder vision tools intentionally return not_implemented responses until their pipelines are built.",
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
            "validation": {"type": "object"},
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
        doc_lines = [spec.description or spec.name.replace("_", " ")]
        if spec.param_description:
            doc_lines.extend(["", "Args:", f"    {spec.param_description}"])
        if spec.result_description:
            doc_lines.extend(["", "Returns:", f"    {spec.result_description}"])
        if spec.safety_notes:
            doc_lines.extend(["", "Safety:", f"    {spec.safety_notes}"])
        if spec.implementation_notes:
            doc_lines.extend(["", "Implementation:", f"    {spec.implementation_notes}"])
        if spec.input_examples:
            doc_lines.extend(["", "Examples:"])
            for index, example in enumerate(spec.input_examples[:2], start=1):
                output = spec.output_examples[index - 1] if spec.output_examples and index <= len(spec.output_examples) else None
                doc_lines.append(f"    {index}. Input: {example}")
                if output is not None:
                    doc_lines.append(f"       Output: {output}")
        spec.executor.__doc__ = "\n".join(doc_lines)
        spec.executor.__name__ = spec.name
        try:
            server.mcp.tool()(spec.executor)
        except Exception:
            # Keep server startup resilient when the MCP runtime rejects a decorator edge case.
            continue

    server.tool_registry = registry
    return registry
