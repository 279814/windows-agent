from __future__ import annotations

from desktop_agent_dev.mcp_server import create_server


def test_server_registers_motion_tool() -> None:
    server = create_server(windows_mcp_root=None)
    assert "motion_preview" in server.tool_registry.specs
    assert server.tool_registry.get("motion_preview").kind == "motion"
