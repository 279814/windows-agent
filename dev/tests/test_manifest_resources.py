from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.manifest import (
    _input_client_hints,
    _input_motion_payload_summary,
    _lighter_input_payload_summary,
    build_manifest,
    build_capabilities,
    build_readme,
    build_tool_handbook,
    build_tool_index,
)
from desktop_agent_dev.tool_registry import RESOURCE_DESCRIPTIONS, build_registry
from desktop_agent_dev.tool_specs.input_tools import register_input_tools
from desktop_agent_dev.tool_specs.motion_tools import register_motion_tools
from desktop_agent_dev.tool_specs.overlay_tools import register_overlay_tools


class DummySafety:
    def check(self, _permission: str) -> bool:
        return True


class DummyExecutor:
    def motion_preview(self, *args, **kwargs):
        return {
            "ok": True,
            "phase": "verified",
            "action": {"kind": "move", "start": {"x": 0, "y": 0}, "end": {"x": 1, "y": 1}, "duration_ms": 180, "easing": "ease_out_quad", "metadata": {}},
            "path": [{"x": 0, "y": 0, "t": 0.0}, {"x": 1, "y": 1, "t": 1.0}],
            "detail": "motion planned",
            "metadata": {"steps": 2},
            "overlay_state": {"visible": False, "cursor_x": 1, "cursor_y": 1, "trail": [[0, 0], [1, 1]], "metadata": {}},
        }


class DummyServices(SimpleNamespace):
    pass


def _registry():
    registry = build_registry()
    services = DummyServices(executor=DummyExecutor(), safety=DummySafety(), perception=object())
    register_input_tools(registry, services)
    register_motion_tools(registry, services)
    register_overlay_tools(registry, services)
    return registry


def test_manifest_exposes_display_uac_and_failure_metadata() -> None:
    manifest = build_manifest(_registry())

    assert "display/DPI normalization" in manifest["summary"]
    assert "UAC-aware recovery" in manifest["summary"]
    assert "failure fallback metadata" in manifest["summary"]
    assert manifest["verification_semantics"]["window_tools"]["multi_source_verification"]
    input_tools = manifest["verification_semantics"]["input_tools"]
    assert input_tools["motion_shaped_tools"]["tools"] == ["input_click", "input_move", "input_drag"]
    assert input_tools["focused_validation_tools"]["tools"] == ["input_type", "input_shortcut"]
    assert input_tools["lighter_dispatch_tools"]["tools"] == ["input_scroll", "input_multi_edit", "input_multi_select"]
    assert "motion_segments" in input_tools["motion_shaped_tools"]["shape"]


def test_resource_index_includes_tool_handbook_and_tool_index_links() -> None:
    resources = {item["uri"]: item for item in _registry().resource_index()}

    assert resources["desktop-agent-dev://tool-handbook"]["description"] == RESOURCE_DESCRIPTIONS["desktop-agent-dev://tool-handbook"]
    assert resources["desktop-agent-dev://tool-index"]["description"] == RESOURCE_DESCRIPTIONS["desktop-agent-dev://tool-index"]


def test_tool_index_matches_catalog_verification_semantics_for_motion_like_inputs() -> None:
    registry = _registry()
    catalog_tools = {tool["name"]: tool for tool in registry.tool_catalog()}
    index_tools = {tool["name"]: tool for tool in build_tool_index(registry)["tools"]}

    for tool_name in ("input_click", "input_move", "input_drag"):
        assert index_tools[tool_name]["verification_semantics"] == catalog_tools[tool_name]["verification_semantics"]


def test_tool_handbook_input_verification_text_mentions_unified_motion_fields() -> None:
    handbook = build_tool_handbook(_registry())

    input_notes = handbook["content"]["verification_semantics"]["input_tools"]
    payload_notes = handbook["content"]["payload_expectations"]["input"]

    assert any("motion_segments.execute" in item for item in input_notes)
    assert any("motion_segments.hover" in item for item in input_notes)
    assert any("target_verification" in item for item in input_notes)
    assert "phase/action/path/metadata/event" in payload_notes


def test_shared_input_payload_summary_is_reused_across_resources() -> None:
    registry = _registry()
    readme = build_readme(registry)
    handbook = build_tool_handbook(registry)

    operator_guidance = readme["sections"][2]["content"]
    payload_notes = handbook["content"]["payload_expectations"]["input"]

    assert any(_input_motion_payload_summary() in item for item in operator_guidance)
    assert any(_lighter_input_payload_summary().replace("for stronger post-action verification", "for post-action confirmation") in item for item in operator_guidance)
    assert _input_motion_payload_summary() in payload_notes
    assert "lighter-dispatch payloads" in payload_notes


def test_capabilities_client_hints_use_input_verification_families() -> None:
    capabilities = build_capabilities(_registry())
    hints = capabilities["sections"][1]["content"]

    assert "input_payload_richness_varies_by_tool" not in hints
    assert hints["input_verification_families_documented"] is True
    assert hints["input_motion_shaped_tools"] == _input_client_hints()["input_motion_shaped_tools"]
    assert hints["input_focused_validation_tools"] == _input_client_hints()["input_focused_validation_tools"]
    assert hints["input_lighter_dispatch_tools"] == _input_client_hints()["input_lighter_dispatch_tools"]
    assert "motion_segments" in hints["input_motion_shaped_payload_fields"]
    assert "lighter-dispatch" in _lighter_input_payload_summary()
