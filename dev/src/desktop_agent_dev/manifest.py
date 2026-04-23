from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .tool_registry import TODO_PLACEHOLDER_TOOLS, ToolRegistry


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
    summary = "Windows desktop agent MCP server for observation, input, window control, and task orchestration."
    body = {
        "name": "desktop-agent-dev",
        "version": "1.5",
        "stage": "phase1",
        "tool_count": len(registry.specs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "links": {
            "handbook": "desktop-agent-dev://tool-handbook",
            "catalog": "desktop-agent-dev://catalog",
            "capabilities": "desktop-agent-dev://capabilities",
            "security": "desktop-agent-dev://security",
            "tool_index": "desktop-agent-dev://tool-index",
        },
        "guidance": [
            "Read the catalog before invoking tools.",
            "Use snapshot tools to observe state before acting.",
            "Treat ocr_extract/ui_match/vision_capture/vision_locate as TODO placeholders until implemented.",
        ],
        "high_risk_actions": ["window_close", "launch_app"],
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Dev Workspace", summary, body)
    chapter["resource"] = "desktop-agent-dev://readme"
    chapter["content"] = body
    return chapter


def build_catalog(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Grouped tool directory with metadata, examples, and implementation status."
    body = {
        "version": "1.5",
        "groups": registry.group_catalog(),
        "tools": registry.tool_catalog(),
        "examples": registry.examples(),
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Tool Catalog", summary, body)
    chapter["resource"] = "desktop-agent-dev://catalog"
    chapter["content"] = body
    return chapter


def build_capabilities(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Server capabilities, client hints, and placeholder status."
    body = {
        "summary": registry.capabilities(),
        "policy": registry.policy(),
        "client_hints": {
            "observe_first": True,
            "tool_handbook_available": True,
            "parameter_help": True,
            "result_help": True,
            "placeholder_tools_require_fallback": True,
        },
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
    chapter = _chapter("Desktop Agent Capabilities", summary, body)
    chapter["resource"] = "desktop-agent-dev://capabilities"
    chapter["content"] = body
    return chapter


def build_security(registry: ToolRegistry) -> dict[str, Any]:
    summary = "Permission model and high-risk action policy."
    body = {
        "default_mode": "observe-first",
        "permission_model": "per-tool",
        "high_risk_actions": ["window_close", "launch_app"],
        "notes": [
            "High-risk actions are guarded by the safety gate.",
            "The server emits only read-only documentation resources and normalized tool metadata.",
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
        "summary": "Formal directory for MCP clients and agents, including placeholder caveats.",
        "sections": [
            {"heading": "Overview", "resource": "desktop-agent-dev://readme", "summary": "Project overview and usage guidance."},
            {"heading": "Tool Catalog", "resource": "desktop-agent-dev://catalog", "summary": "Grouped tool directory with metadata and examples."},
            {"heading": "Capabilities", "resource": "desktop-agent-dev://capabilities", "summary": "Server capabilities and client hints."},
            {"heading": "Security", "resource": "desktop-agent-dev://security", "summary": "Permission model and high-risk action policy."},
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
        "version": "1.5",
        "stage": "phase1",
        "high_risk_actions": ["window_close", "launch_app"],
        "close_semantics": {
            "preferred_backend": "close_app",
            "success_rule": "backend exit code is 0 or absent and detail does not start with Failed/Error",
        },
        "resources": [
            {"uri": "desktop-agent-dev://readme", "title": "README"},
            {"uri": "desktop-agent-dev://catalog", "title": "Catalog"},
            {"uri": "desktop-agent-dev://capabilities", "title": "Capabilities"},
            {"uri": "desktop-agent-dev://security", "title": "Security"},
            {"uri": "desktop-agent-dev://tool-handbook", "title": "Tool Handbook"},
            {"uri": "desktop-agent-dev://tool-index", "title": "Tool Index"},
        ],
        "handbook_uri": "desktop-agent-dev://tool-handbook",
        "tool_index_uri": "desktop-agent-dev://tool-index",
        "readme_uri": "desktop-agent-dev://readme",
        "catalog_uri": "desktop-agent-dev://catalog",
        "capabilities_uri": "desktop-agent-dev://capabilities",
        "security_uri": "desktop-agent-dev://security",
        "summary": "MCP document directory for the desktop agent workspace.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_count": len(registry.specs),
        "todo_placeholders": list(TODO_PLACEHOLDER_TOOLS),
    }
