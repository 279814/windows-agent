from __future__ import annotations

from typing import Any

from ..schemas import ok
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_vision_tools(registry: ToolRegistry, services: Any) -> None:
    def vision_capture() -> dict[str, Any]:
        return ok("vision_capture", {"status": "placeholder", "mode": "capture", "source": "registry-only"})

    def ocr_extract() -> dict[str, Any]:
        return ok("ocr_extract", {"status": "placeholder", "mode": "ocr", "source": "registry-only"})

    def vision_locate() -> dict[str, Any]:
        return ok("vision_locate", {"status": "placeholder", "mode": "locate", "source": "registry-only"})

    def ui_match() -> dict[str, Any]:
        return ok("ui_match", {"status": "placeholder", "mode": "match", "source": "registry-only"})

    registry.register(ToolSpec(name="vision_capture", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_capture, description="Capture a vision placeholder. Use this when you need a screenshot-oriented handoff for later image understanding work.\n\nParameters: none.\nReturns: a placeholder capture payload.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder capture payload.", input_examples=[{}], output_examples=[{"ok": True, "tool": "vision_capture", "data": {"status": "placeholder", "mode": "capture", "source": "registry-only"}}], safety_notes="Read-only.", implementation_notes="Registry-only placeholder until the vision pipeline lands."))
    registry.register(ToolSpec(name="ocr_extract", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ocr_extract, description="Extract text with an OCR placeholder. Use this when you need text from a screen before full OCR support exists.\n\nParameters: none.\nReturns: a placeholder OCR payload.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder OCR payload.", input_examples=[{}], output_examples=[{"ok": True, "tool": "ocr_extract", "data": {"status": "placeholder", "mode": "ocr", "source": "registry-only"}}], safety_notes="Read-only.", implementation_notes="Registry-only placeholder until the OCR pipeline lands."))
    registry.register(ToolSpec(name="vision_locate", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_locate, description="Locate visual elements with a placeholder interface. Use this when you need future coordinate-based vision targeting.\n\nParameters: none.\nReturns: a placeholder locate payload.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder locate payload.", input_examples=[{}], output_examples=[{"ok": True, "tool": "vision_locate", "data": {"status": "placeholder", "mode": "locate", "source": "registry-only"}}], safety_notes="Read-only.", implementation_notes="Registry-only placeholder until the locator pipeline lands."))
    registry.register(ToolSpec(name="ui_match", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ui_match, description="Match UI structure with a placeholder interface. Use this when you need future UIA alignment or structural comparison support.\n\nParameters: none.\nReturns: a placeholder match payload.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder match payload.", input_examples=[{}], output_examples=[{"ok": True, "tool": "ui_match", "data": {"status": "placeholder", "mode": "match", "source": "registry-only"}}], safety_notes="Read-only.", implementation_notes="Registry-only placeholder until UI matching lands."))
