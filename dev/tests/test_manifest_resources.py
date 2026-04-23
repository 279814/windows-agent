from __future__ import annotations

from desktop_agent_dev.mcp_server import create_server


def test_manifest_exposes_display_uac_and_failure_metadata() -> None:
    server = create_server(windows_mcp_root=None)

    manifest = server.manifest
    assert "display/DPI normalization" in manifest["summary"]
    assert "UAC-aware recovery" in manifest["summary"]
    assert "failure fallback metadata" in manifest["summary"]
    assert manifest["verification_semantics"]["window_tools"]["multi_source_verification"]


def test_tool_discovery_includes_new_focus_hints() -> None:
    server = create_server(windows_mcp_root=None)

    discovery = server.tool_discovery
    assert discovery["version"] == "1.6"
    assert "failure-banner" in discovery["layout"]["recommended_components"]
    assert "display-context-chip" in discovery["layout"]["recommended_components"]
    assert discovery["summary"].find("failure fallback guidance") != -1
