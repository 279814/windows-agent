def test_package_smoke():
    import desktop_agent

    assert desktop_agent is not None


def test_smoke_manifest_and_registry_surface_window_close() -> None:
    from desktop_agent_dev.mcp_server import create_server
    from desktop_agent_dev.manifest import build_manifest

    server = create_server()
    manifest = build_manifest(server.tool_registry)

    assert "window_close" in server.tool_registry.specs
    assert server.tool_registry.specs["window_close"].backend_method == "close_app"
    assert "window_close" in manifest["high_risk_actions"]
    assert manifest["tool_count"] == len(server.tool_registry.specs)
