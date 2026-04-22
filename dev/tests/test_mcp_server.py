from __future__ import annotations

import asyncio

from mcp import ClientSession, StdioServerParameters, stdio_client

from desktop_agent_dev.mcp_server import create_server


RESOURCE_URIS = [
    "desktop-agent-dev://readme",
    "desktop-agent-dev://catalog",
    "desktop-agent-dev://capabilities",
    "desktop-agent-dev://security",
    "desktop-agent-dev://manifest",
    "desktop-agent-dev://tool-handbook",
    "desktop-agent-dev://tool-index",
]


def test_server_registers_tools() -> None:
    server = create_server()
    assert server.mcp is not None
    assert server.services is not None


def test_server_tools_return_structured_payloads() -> None:
    server = create_server()
    snapshot = server.services.perception.snapshot()
    assert snapshot.metadata["status"] == "stubbed"
    assert snapshot.metadata["source"] == "dev-workspace"


def test_server_registers_window_tools() -> None:
    server = create_server()
    assert server.services.executor.switch_window("main").tool == "window_switch"
    assert server.services.executor.resize_window(name="main", width=100, height=200).tool == "window_resize"


async def _mcp_smoke_chain() -> dict[str, object]:
    params = StdioServerParameters(
        command="python",
        args=["-m", "desktop_agent_dev"],
        cwd="E:/developdata/code/windows-mcp/dev",
        env={"PYTHONPATH": "E:/developdata/code/windows-mcp/dev/src"},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init = await session.initialize()
            resources = await session.list_resources()
            resource_uris = [str(item.uri) for item in resources.resources]
            read_results = {}
            for uri in RESOURCE_URIS:
                result = await session.read_resource(uri)
                read_results[uri] = result
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            snapshot = await session.call_tool("desktop_snapshot", {"with_screenshot": False})
            move = await session.call_tool("input_move", {"x": 10, "y": 20})
            window_switch = await session.call_tool("window_switch", {"name": "main"})
            window_focus = await session.call_tool("window_focus", {"name": "main"})
            window_resize = await session.call_tool("window_resize", {"name": "main", "width": 640, "height": 480})
            task_plan = await session.call_tool("task_plan", {"goal": "打开记事本并输入 hello"})
            task_state = await session.call_tool("task_state", {"task_id": "demo"})
            vision_capture = await session.call_tool("vision_capture", {})
            ocr_extract = await session.call_tool("ocr_extract", {})
            ui_match = await session.call_tool("ui_match", {})
            return {
                "initialize": init,
                "resource_uris": resource_uris,
                "read_results": read_results,
                "tool_names": tool_names,
                "snapshot": snapshot,
                "move": move,
                "window_switch": window_switch,
                "window_focus": window_focus,
                "window_resize": window_resize,
                "task_plan": task_plan,
                "task_state": task_state,
                "vision_capture": vision_capture,
                "ocr_extract": ocr_extract,
                "ui_match": ui_match,
            }


def test_mcp_smoke_chain() -> None:
    result = asyncio.run(_mcp_smoke_chain())
    assert "desktop-agent-dev://readme" in result["resource_uris"]
    assert "desktop-agent-dev://tool-index" in result["resource_uris"]
    assert "desktop_snapshot" in result["tool_names"]
    assert "input_move" in result["tool_names"]
    assert "window_switch" in result["tool_names"]
    assert "window_focus" in result["tool_names"]
    assert "window_resize" in result["tool_names"]
    assert "task_plan" in result["tool_names"]
    assert "task_state" in result["tool_names"]
    assert "vision_capture" in result["tool_names"]
    assert "ocr_extract" in result["tool_names"]
    assert "ui_match" in result["tool_names"]
    assert result["snapshot"].content
    assert result["move"].content
    assert result["window_switch"].content
    assert result["window_focus"].content
    assert result["window_resize"].content
    assert result["task_plan"].content
    assert result["task_state"].content
    assert result["vision_capture"].content
    assert result["ocr_extract"].content
    assert result["ui_match"].content
