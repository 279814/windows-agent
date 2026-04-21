from desktop_agent_dev.mcp_server import create_server


def test_registry_exposes_group_metadata() -> None:
    server = create_server()
    registry = server.tool_registry
    metadata = registry.metadata()

    assert metadata["version"] == "1.1"
    assert metadata["stage"] == "phase1"
    assert metadata["capabilities"]["ocr_hooks"] is True
    assert metadata["capabilities"]["vision_hooks"] is True
    assert metadata["client_hints"]["tool_summary"] is True
    assert {group["kind"] for group in metadata["groups"]} >= {"snapshot", "input", "window", "task"}


def test_registry_contains_desktop_metadata() -> None:
    server = create_server()
    spec = server.tool_registry.specs["desktop_snapshot"]

    assert spec.description
    assert spec.examples == [{"with_screenshot": False}, {"with_screenshot": True}]
    assert spec.result_schema["required"] == ["ok", "tool"]


def test_registry_contains_input_and_window_metadata() -> None:
    server = create_server()
    registry = server.tool_registry

    assert registry.specs["input_click"].permission == "click"
    assert registry.specs["input_multi_edit"].examples
    assert registry.specs["window_resize"].description
    assert registry.specs["window_restore"].kind == "window"


def test_registry_contains_vision_placeholders() -> None:
    server = create_server()
    registry = server.tool_registry

    assert registry.specs["vision_capture"].kind == "snapshot"
    assert registry.specs["ocr_extract"].description
    assert registry.specs["vision_locate"].result_schema["required"] == ["ok", "tool"]
    assert registry.specs["ui_match"].examples == [{}]
