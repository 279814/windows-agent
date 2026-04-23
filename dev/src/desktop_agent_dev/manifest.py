from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .tool_registry import RESOURCE_DESCRIPTIONS, TODO_PLACEHOLDER_TOOLS, ToolRegistry


RESOURCE_SECTIONS = (
    ("Overview", "readme", "desktop-agent-dev://readme"),
    ("Tool Catalog", "catalog", "desktop-agent-dev://catalog"),
    ("Capabilities", "capabilities", "desktop-agent-dev://capabilities"),
    ("Security", "security", "desktop-agent-dev://security"),
)


def _chapter(title: str, summary: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": title,
        "summary": summary,
        "sections": [
            {
                "heading": "Purpose",
                "content": summary,
            },
            {
                "heading": "Content",
                "content": body,
            },
        ],
    }


def build_readme(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Windows desktop agent MCP server for observation, input, window control, and task orchestration, with explicit verification semantics, handle/pid target selection guidance, and TODO placeholders."
    body = {
        "name": "desktop-agent-dev",
        "version": "1.6",
        "stage": "phase1",
        "tool_count": len(registry.specs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "links": {
            "manifest": "desktop-agent-dev://manifest",
            "handbook": "desktop-agent-dev://tool-handbook",
            "catalog": "desktop-agent-dev://catalog",
            "capabilities": "desktop-agent-dev://capabilities",
            "security": "desktop-agent-dev://security",
            "tool_index": "desktop-agent-dev://tool-index",
        },
        "guidance": [
            "Read the catalog or tool-handbook before invoking tools.",
            "Use snapshot tools to observe state before acting.",
            "Prefer handle-aware verification fields such as verified, matched_by, before_handle, after_handle, verification_mode, and backend_response_code when auditing window-tool results.",
            "Input tools vary in payload richness: click/type/shortcut expose stronger verification fields, while move/drag/scroll/multi-* actions may need desktop_snapshot pairing for post-action confirmation.",
            "Window tools accept name, handle, or pid selectors. Targeting precedence is handle > pid > name, so prefer handle in duplicate-title scenarios.",
            "Maximize/minimize/close verification may rely on multiple signals, including status, handle visibility, active-window changes, geometry changes, or matching-window count deltas.",
            "Treat ocr_extract/ui_match/vision_capture/vision_locate as TODO placeholders until implemented.",
        ],
        "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Dev Workspace", summary, body)
    chapter["resource"] = "desktop-agent-dev://readme"
    chapter["content"] = body
    return chapter


def build_catalog(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Grouped tool directory with metadata, examples, implementation status, verification semantics, handle/pid targeting notes, and TODO placeholders."
    body = {
        "version": "1.6",
        "groups": registry.group_catalog(),
        "tools": registry.tool_catalog(),
        "examples": registry.examples(),
        "resource_index": registry.resource_index(),
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Tool Catalog", summary, body)
    chapter["resource"] = "desktop-agent-dev://catalog"
    chapter["content"] = body
    return chapter


def build_capabilities(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Server capabilities, client hints, verification affordances, and placeholder status."
    body = {
        "summary": registry.capabilities(),
        "policy": registry.policy(),
        "client_hints": {
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
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Capabilities", summary, body)
    chapter["resource"] = "desktop-agent-dev://capabilities"
    chapter["content"] = body
    return chapter


def build_security(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Permission model and high-risk action policy, with verification-oriented operating notes and placeholder caveats."
    body = {
        "default_mode": "observe-first",
        "permission_model": "per-tool",
        "high_risk_actions": ["window_close", "window_launch", "input_launch_app"],
        "notes": [
            "High-risk actions are guarded by the safety gate.",
            "The server emits only read-only documentation resources and normalized tool metadata.",
            "Window-control success is verification-driven: backend success alone is not treated as sufficient when foreground, handle, visibility, or geometry checks disagree.",
            "Input actions with lightweight payloads are still safe to expose, but clients should pair them with fresh observations when they need stronger auditability.",
            "Placeholder vision tools are intentionally exposed as TODO/not-implemented so clients can branch to fallback strategies.",
        ],
        "policy": registry.policy(),
    }
    chapter = _chapter("Desktop Agent Security", summary, body)
    chapter["resource"] = "desktop-agent-dev://security"
    chapter["content"] = body
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
            "readme": build_readme(registry),
            "catalog": build_catalog(registry),
            "capabilities": build_capabilities(registry),
            "security": build_security(registry),
        },
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
