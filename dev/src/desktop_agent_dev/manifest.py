from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .tool_registry import RESOURCE_DESCRIPTIONS, TODO_PLACEHOLDER_TOOLS, ToolRegistry


def _chapter(title: str, summary: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": title,
        "summary": summary,
        "sections": sections,
    }


def build_readme(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Windows desktop agent MCP server for observation, input, window control, and task orchestration, with explicit verification semantics, handle/pid target selection guidance, and TODO placeholders."
    chapter = _chapter(
        "Desktop Agent Dev Workspace",
        summary,
        [
            {
                "heading": "Overview",
                "content": {
                    "name": "desktop-agent-dev",
                    "version": "1.6",
                    "stage": "phase1",
                    "tool_count": len(registry.specs),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "summary": summary,
                },
            },
            {
                "heading": "What This Server Covers",
                "content": [
                    "Desktop observation through normalized snapshots of windows, focused controls, UIA tree nodes, and optional screenshots.",
                    "Desktop input primitives such as click, move, drag, scroll, typing, shortcuts, multi-edit, and multi-select.",
                    "Window lifecycle control with name/handle/pid targeting plus verification-driven launch, switch, focus, resize, minimize, maximize, restore, and close behavior.",
                    "Task planning/state helpers for observe -> act -> verify workflows.",
                ],
            },
            {
                "heading": "Operator Guidance",
                "content": [
                    "Read the catalog or tool-handbook before invoking unfamiliar tools.",
                    "Use snapshot tools to observe state before acting.",
                    "Prefer handle-aware verification fields such as verified, matched_by, before_handle, after_handle, verification_mode, and backend_response_code when auditing window-tool results.",
                    "Input tools vary in payload richness: click/type/shortcut expose stronger verification fields, while move/drag/scroll/multi-* actions may need desktop_snapshot pairing for post-action confirmation.",
                    "Window tools accept name, handle, or pid selectors. Targeting precedence is handle > pid > name, so prefer handle in duplicate-title scenarios.",
                    "Maximize/minimize/close verification may rely on multiple signals, including status, handle visibility, active-window changes, geometry changes, or matching-window count deltas.",
                    "Treat ocr_extract/ui_match/vision_capture/vision_locate as TODO placeholders until implemented.",
                ],
            },
            {
                "heading": "Resource Links",
                "content": registry.resource_index(),
            },
            {
                "heading": "Risk Notes",
                "content": {
                    "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
                    "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
                },
            },
        ],
    )
    chapter["resource"] = "desktop-agent-dev://readme"
    return chapter


def build_catalog(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Grouped tool directory with metadata, examples, implementation status, verification semantics, handle/pid targeting notes, and TODO placeholders."
    grouped_tools = []
    tool_lookup = {tool["name"]: tool for tool in registry.tool_catalog()}
    for group in registry.group_catalog():
        grouped_tools.append(
            {
                "kind": group["kind"],
                "title": group["title"],
                "tools": [
                    {
                        "name": name,
                        "description": tool_lookup[name]["description"],
                        "implementation_status": tool_lookup[name]["implementation_status"],
                        "verification_semantics": tool_lookup[name]["verification_semantics"],
                        "targeting_semantics": tool_lookup[name]["targeting_semantics"],
                        "backend_method": tool_lookup[name]["backend_method"],
                    }
                    for name in group["tools"]
                ],
            }
        )
    chapter = _chapter(
        "Desktop Agent Tool Catalog",
        summary,
        [
            {
                "heading": "Catalog Summary",
                "content": {
                    "version": "1.6",
                    "group_count": len(grouped_tools),
                    "tool_count": len(registry.specs),
                    "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
                },
            },
            {
                "heading": "Grouped Tools",
                "content": grouped_tools,
            },
            {
                "heading": "Examples",
                "content": registry.examples(),
            },
        ],
    )
    chapter["resource"] = "desktop-agent-dev://catalog"
    return chapter


def build_capabilities(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Server capabilities, client hints, verification affordances, and placeholder status."
    chapter = _chapter(
        "Desktop Agent Capabilities",
        summary,
        [
            {
                "heading": "Capability Matrix",
                "content": registry.capabilities(),
            },
            {
                "heading": "Client Hints",
                "content": {
                    "observe_first": True,
                    "tool_handbook_available": True,
                    "parameter_help": True,
                    "result_help": True,
                    "verification_fields_available": True,
                    "window_handle_pid_targeting_available": True,
                    "window_multi_source_verification_documented": True,
                    "input_payload_richness_varies_by_tool": True,
                    "placeholder_tools_require_fallback": True,
                },
            },
            {
                "heading": "Risk Posture",
                "content": registry.policy(),
            },
        ],
    )
    chapter["resource"] = "desktop-agent-dev://capabilities"
    return chapter


def build_security(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Permission model and high-risk action policy, with verification-oriented operating notes and placeholder caveats."
    chapter = _chapter(
        "Desktop Agent Security",
        summary,
        [
            {
                "heading": "Permission Model",
                "content": {
                    "default_mode": "observe-first",
                    "permission_model": "per-tool",
                    "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
                },
            },
            {
                "heading": "Operating Notes",
                "content": [
                    "High-risk actions are guarded by the safety gate.",
                    "The server emits read-only documentation resources plus normalized tool metadata for client-side catalogs.",
                    "Window-control success is verification-driven: backend success alone is not treated as sufficient when foreground, handle, visibility, or geometry checks disagree.",
                    "Input actions with lighter payloads are still safe to expose, but clients should pair them with fresh observations when they need stronger auditability.",
                    "Placeholder vision tools are intentionally exposed as TODO/not-implemented so clients can branch to fallback strategies.",
                ],
            },
            {
                "heading": "Policy",
                "content": registry.policy(),
            },
        ],
    )
    chapter["resource"] = "desktop-agent-dev://security"
    return chapter


def build_tool_handbook(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "tool-handbook",
        "title": "Desktop Agent Tool Handbook",
        "summary": "Formal directory for MCP clients and agents, including verification semantics, handle/pid targeting rules, input payload expectations, and TODO placeholders.",
        "sections": [
            {"heading": "Overview", "resource": "desktop-agent-dev://readme", "summary": RESOURCE_DESCRIPTIONS["desktop-agent-dev://readme"]},
            {"heading": "Tool Catalog", "resource": "desktop-agent-dev://catalog", "summary": RESOURCE_DESCRIPTIONS["desktop-agent-dev://catalog"]},
            {"heading": "Capabilities", "resource": "desktop-agent-dev://capabilities", "summary": RESOURCE_DESCRIPTIONS["desktop-agent-dev://capabilities"]},
            {"heading": "Security", "resource": "desktop-agent-dev://security", "summary": RESOURCE_DESCRIPTIONS["desktop-agent-dev://security"]},
        ],
        "content": {
            "when_to_read_which_resource": [
                "Use manifest when a client needs machine-readable resource links, versioning, verification semantics, and discovery metadata.",
                "Use readme for operator-facing overview and server usage guidance.",
                "Use catalog for grouped tool descriptions, examples, and implementation status.",
                "Use tool-index for compact per-tool lookup without the full handbook body.",
                "Use capabilities and security when a client needs feature gating, risk posture, or fallback policy.",
            ],
            "verification_semantics": {
                "window_tools": [
                    "Top-level ok reflects the verified desktop outcome, not only backend success.",
                    "Prefer handle or pid selectors when available.",
                    "Inspect verified, matched_by, before_handle, after_handle, verification_mode, backend_response_detail, and backend_response_code.",
                    "Modern/UWP-style windows may verify via native visibility, iconic/zoomed state, geometry expansion, or matching-window-count deltas.",
                ],
                "input_tools": [
                    "input_type exposes explicit validation and focused_control snapshots.",
                    "input_shortcut exposes foreground focus before/after plus raw injection_result.",
                    "input_click may expose hit-test metadata when the backend resolves the clicked surface.",
                    "move/drag/scroll/multi-* actions may require desktop_snapshot pairing for stronger post-action verification.",
                ],
                "todo_placeholders": "ocr_extract, ui_match, vision_capture, and vision_locate remain TODO placeholders and intentionally return not_implemented.",
            },
            "targeting_semantics": {
                "precedence": "handle > pid > name",
                "guidance": [
                    "Use handle for duplicate-title windows.",
                    "Use pid for process-level targeting when multiple windows share near-identical names.",
                    "Name matching is normalized for lightweight title variants such as unsaved markers, but explicit selectors remain more reliable.",
                ],
            },
            "payload_expectations": {
                "snapshot": "Rich normalized observation payloads intended for observe-first workflows.",
                "input": "Payload richness varies by action. Some tools confirm dispatch only; others include focused control, hit-test, or focus-state verification.",
                "window": "Payloads include before/after target context, backend responses, and verification-oriented fields.",
                "task": "Planner/state payloads describe workflow progress rather than desktop side effects.",
            },
        },
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }


def build_tool_index(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "tool-index",
        "title": "Desktop Agent Tool Index",
        "summary": "Normalized tool index for MCP clients with implementation status, verification semantics, targeting semantics, result semantics, and TODO placeholders.",
        "version": "1.6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups": registry.group_catalog(),
        "tools": [
            {
                "name": tool["name"],
                "kind": tool["kind"],
                "description": tool["description"],
                "implementation_status": tool["implementation_status"],
                "verification_semantics": tool["verification_semantics"],
                "targeting_semantics": tool["targeting_semantics"],
                "result_description": tool["result_description"],
                "permission": tool["permission"],
            }
            for tool in registry.tool_catalog()
        ],
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }


def build_manifest(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "desktop-agent-dev",
        "title": "Desktop Agent Dev Workspace",
        "version": "1.6",
        "stage": "phase1",
        "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
        "close_semantics": {
            "preferred_backend": "close_app",
            "success_rule": "backend exit code is 0 or absent and detail does not start with Failed/Error",
        },
        "verification_semantics": {
            "window_tools": {
                "target_selection": "Handle wins over pid, and pid wins over name. Prefer handle for duplicate titles and pid for process-level disambiguation.",
                "success_rule": "Top-level ok reflects the verified desktop outcome, not only backend success.",
                "inspection_fields": [
                    "verified",
                    "matched_by",
                    "before_handle",
                    "after_handle",
                    "verification_mode",
                    "backend_response_detail",
                    "backend_response_code",
                ],
                "multi_source_verification": "Window tools may verify through status, handle visibility, active-window changes, geometry changes, or matching-window count deltas depending on the action.",
            },
            "input_tools": {
                "high_signal_tools": ["input_click", "input_type", "input_shortcut"],
                "dispatch_confirming_tools": ["input_move", "input_drag", "input_scroll", "input_multi_edit", "input_multi_select"],
                "guidance": "Use validation blocks, focus fields, or hit-test metadata when available; otherwise pair the action with desktop_snapshot for post-action verification.",
            },
            "placeholder_tools": "ocr_extract, ui_match, vision_capture, and vision_locate are TODO placeholders and intentionally return not_implemented.",
        },
        "resources": registry.resource_index(),
        "handbook_uri": "desktop-agent-dev://tool-handbook",
        "tool_index_uri": "desktop-agent-dev://tool-index",
        "readme_uri": "desktop-agent-dev://readme",
        "catalog_uri": "desktop-agent-dev://catalog",
        "capabilities_uri": "desktop-agent-dev://capabilities",
        "security_uri": "desktop-agent-dev://security",
        "summary": "MCP document directory for the desktop agent workspace, including verification semantics, handle/pid targeting guidance, multi-source window verification rules, and TODO placeholders.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_count": len(registry.specs),
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
