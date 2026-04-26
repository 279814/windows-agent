from __future__ import annotations

from types import SimpleNamespace

from desktop_agent_dev.tool_registry import build_registry
from desktop_agent_dev.tool_specs.input_tools import register_input_tools


class DummySafety:
    def check(self, _permission: str) -> bool:
        return True


class DummyServices(SimpleNamespace):
    pass


def test_input_motion_like_tool_docs_reference_unified_motion_schema() -> None:
    registry = build_registry()
    services = DummyServices(executor=object(), safety=DummySafety(), perception=object())

    register_input_tools(registry, services)

    for tool_name in ("input_click", "input_move", "input_drag"):
        spec = registry.get(tool_name)
        payload = spec.output_examples[0]["data"]["payload"]
        doc_text = " ".join((spec.description, spec.result_description, spec.implementation_notes))

        assert "motion schema" in doc_text or "motion-shaped payload" in doc_text
        assert "motion_segments" in doc_text
        assert payload["phase"] == "verified"
        assert "action" in payload
        assert "path" in payload
        assert "metadata" in payload
        assert "event" in payload
        assert "motion" in payload
        assert "motion_segments" in payload


def test_input_motion_like_tool_registry_semantics_are_precise() -> None:
    registry = build_registry()
    services = DummyServices(executor=object(), safety=DummySafety(), perception=object())

    register_input_tools(registry, services)
    catalog = {item["name"]: item for item in registry.tool_catalog()}

    click_semantics = catalog["input_click"]["verification_semantics"]
    move_semantics = catalog["input_move"]["verification_semantics"]
    drag_semantics = catalog["input_drag"]["verification_semantics"]

    assert "target_verification" in click_semantics
    assert "motion_segments" in click_semantics
    assert "motion_segments.execute" in move_semantics
    assert "target_verification" in move_semantics
    assert "motion_segments.hover" in drag_semantics
    assert "active_window_before/after" in drag_semantics


def test_registry_uses_lighter_dispatch_family_wording_for_light_input_tools() -> None:
    registry = build_registry()
    services = DummyServices(executor=object(), safety=DummySafety(), perception=object())

    register_input_tools(registry, services)
    catalog = {item["name"]: item for item in registry.tool_catalog()}

    for tool_name in ("input_scroll", "input_multi_edit", "input_multi_select"):
        assert "lighter-dispatch" in catalog[tool_name]["verification_semantics"]
