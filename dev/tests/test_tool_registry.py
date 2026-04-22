from desktop_agent_dev.mcp_server import create_server


def test_registry_exposes_group_metadata() -> None:
    server = create_server()
    registry = server.tool_registry
    metadata = registry.metadata()

    assert metadata["version"] == "1.5"
    assert metadata["summary"]
    assert metadata["stage"] == "phase1"
    assert set(metadata["capabilities"]) >= {"snapshot", "input", "window", "task"}
    assert metadata["capabilities"]["supports_handshake_metadata"] is True
    assert metadata["policy"]["default_mode"] == "observe-first"
    assert metadata["policy"]["permission_model"] == "per-tool"
    assert metadata["tool_catalog"]
    assert metadata["group_catalog"]
    assert metadata["examples"]


def test_registry_contains_desktop_metadata() -> None:
    server = create_server()
    spec = server.tool_registry.specs["desktop_snapshot"]

    assert spec.description.startswith("Capture the current desktop state")
    assert spec.param_description
    assert spec.result_description
    assert spec.input_examples == [{"with_screenshot": False}, {"with_screenshot": True}]
    assert spec.output_examples
    assert spec.safety_notes
    assert spec.implementation_notes
    assert spec.result_schema["required"] == ["ok", "tool"]


def test_registry_contains_input_and_window_metadata() -> None:
    server = create_server()
    registry = server.tool_registry

    assert registry.specs["input_click"].permission == "click"
    assert registry.specs["input_multi_edit"].input_examples
    assert registry.specs["input_shortcut"].param_description
    assert registry.specs["window_resize"].description
    assert registry.specs["window_restore"].kind == "window"
    assert registry.specs["window_launch"].safety_notes


def test_registry_contains_vision_placeholders() -> None:
    server = create_server()
    registry = server.tool_registry

    assert registry.specs["vision_capture"].kind == "snapshot"
    assert registry.specs["ocr_extract"].description
    assert registry.specs["vision_locate"].result_schema["required"] == ["ok", "tool"]
    assert registry.specs["ui_match"].input_examples == [{}]
    assert registry.specs["ui_match"].output_examples
