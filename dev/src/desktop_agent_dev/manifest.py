from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .tool_registry import ToolRegistry


def build_readme(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "desktop-agent-dev",
        "title": "Desktop Agent Dev Workspace",
        "summary": "Windows desktop agent MCP server for observation, input, window control, and task orchestration.",
        "version": "1.4",
        "stage": "phase1",
        "handbook_uri": "desktop-agent-dev://tool-handbook",
        "tool_index_uri": "desktop-agent-dev://tool-index",
        "readme_uri": "desktop-agent-dev://readme",
        "catalog_uri": "desktop-agent-dev://catalog",
        "capabilities_uri": "desktop-agent-dev://capabilities",
        "security_uri": "desktop-agent-dev://security",
        "description": (
            "This server exposes a Windows desktop automation surface for MCP clients such as Cursor, Claude, and Codex. "
            "It follows an observe-first workflow with grouped tool catalogs and safety-gated window/input actions."
        ),
        "usage": [
            "Read the catalog before invoking tools.",
            "Use snapshot tools to observe state before acting.",
            "Treat window close and app launch as gated operations.",
        ],
        "tool_count": len(registry.specs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_catalog(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "version": "1.4",
        "title": "Desktop Agent Tool Catalog",
        "groups": registry.group_catalog(),
        "tools": registry.tool_catalog(),
        "examples": registry.examples(),
    }


def build_capabilities(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "title": "Desktop Agent Capabilities",
        "summary": registry.capabilities(),
        "policy": registry.policy(),
        "client_hints": {
            "observe_first": True,
            "tool_handbook_available": True,
            "parameter_help": True,
            "result_help": True,
        },
    }


def build_security(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "title": "Desktop Agent Security",
        "default_mode": "observe-first",
        "permission_model": "per-tool",
        "high_risk_actions": ["window_close", "launch_app"],
        "notes": [
            "High-risk actions are guarded by the safety gate.",
            "The server emits only read-only documentation resources and normalized tool metadata.",
        ],
        "policy": registry.policy(),
    }


def build_tool_handbook(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "tool-handbook",
        "title": "Desktop Agent Tool Handbook",
        "sections": [
            {
                "id": "readme",
                "title": "README",
                "resource": "desktop-agent-dev://readme",
                "summary": "Project overview and usage guidance.",
            },
            {
                "id": "catalog",
                "title": "Catalog",
                "resource": "desktop-agent-dev://catalog",
                "summary": "Grouped tool directory with metadata and examples.",
            },
            {
                "id": "capabilities",
                "title": "Capabilities",
                "resource": "desktop-agent-dev://capabilities",
                "summary": "Server capabilities and client hints.",
            },
            {
                "id": "security",
                "title": "Security",
                "resource": "desktop-agent-dev://security",
                "summary": "Permission model and high-risk action policy.",
            },
        ],
        "catalog": build_catalog(registry),
    }


def build_manifest(registry: ToolRegistry) -> dict[str, Any]:
    return {
        "name": "desktop-agent-dev",
        "title": "Desktop Agent Dev Workspace",
        "version": "1.4",
        "stage": "phase1",
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
    }
