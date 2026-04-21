from desktop_agent_dev.mcp_server import create_server


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
