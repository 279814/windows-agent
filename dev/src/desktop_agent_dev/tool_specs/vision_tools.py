from __future__ import annotations

from typing import Any

from ..schemas import ToolResponse
from ..tool_registry import RESULT_SCHEMAS, ToolRegistry, ToolSpec


def register_vision_tools(registry: ToolRegistry, services: Any) -> None:
    def _not_implemented(tool: str, mode: str, capability: str) -> dict[str, Any]:
        payload = {
            "status": "placeholder",
            "state": "not_implemented",
            "implemented": False,
            "available": False,
            "mode": mode,
            "source": "registry-only",
            "capability": capability,
        }
        message = f"{tool} is a placeholder and is not implemented"
        return ToolResponse(
            ok=False,
            tool=tool,
            message=message,
            data=payload,
            error={"code": "not_implemented", "message": message},
        ).as_dict()

    def vision_capture() -> dict[str, Any]:
        return _not_implemented("vision_capture", "capture", "vision_capture")

    def ocr_extract() -> dict[str, Any]:
        return _not_implemented("ocr_extract", "ocr", "ocr_extract")

    def vision_locate() -> dict[str, Any]:
        return _not_implemented("vision_locate", "locate", "vision_locate")

    def ui_match() -> dict[str, Any]:
        return _not_implemented("ui_match", "match", "ui_match")

    registry.register(ToolSpec(name="vision_capture", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_capture, description="Capture a vision placeholder. TODO: implement screenshot-oriented handoff for later image understanding work.\n\nParameters: none.\nReturns: a placeholder response that explicitly reports the capability as not implemented.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder response with compatible data fields plus explicit TODO/not-implemented semantics.", input_examples=[{}], output_examples=[{"ok": False, "tool": "vision_capture", "message": "vision_capture is a placeholder and is not implemented", "data": {"status": "placeholder", "state": "not_implemented", "implemented": False, "available": False, "mode": "capture", "source": "registry-only", "capability": "vision_capture"}, "error": {"code": "not_implemented", "message": "vision_capture is a placeholder and is not implemented"}}], safety_notes="Read-only.", implementation_notes="TODO placeholder only. Registry-only until the vision pipeline lands; returns explicit not-implemented semantics instead of a success-shaped payload."))
    registry.register(ToolSpec(name="ocr_extract", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ocr_extract, description="Extract text with an OCR placeholder. TODO: implement OCR extraction for screen text.\n\nParameters: none.\nReturns: a placeholder response that explicitly reports the capability as not implemented.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder response with compatible data fields plus explicit TODO/not-implemented semantics.", input_examples=[{}], output_examples=[{"ok": False, "tool": "ocr_extract", "message": "ocr_extract is a placeholder and is not implemented", "data": {"status": "placeholder", "state": "not_implemented", "implemented": False, "available": False, "mode": "ocr", "source": "registry-only", "capability": "ocr_extract"}, "error": {"code": "not_implemented", "message": "ocr_extract is a placeholder and is not implemented"}}], safety_notes="Read-only.", implementation_notes="TODO placeholder only. Registry-only until the OCR pipeline lands; returns explicit not-implemented semantics instead of a success-shaped payload."))
    registry.register(ToolSpec(name="vision_locate", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_locate, description="Locate visual elements with a placeholder interface. TODO: implement coordinate-oriented visual target finding.\n\nParameters: none.\nReturns: a placeholder response that explicitly reports the capability as not implemented.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder response with compatible data fields plus explicit TODO/not-implemented semantics.", input_examples=[{}], output_examples=[{"ok": False, "tool": "vision_locate", "message": "vision_locate is a placeholder and is not implemented", "data": {"status": "placeholder", "state": "not_implemented", "implemented": False, "available": False, "mode": "locate", "source": "registry-only", "capability": "vision_locate"}, "error": {"code": "not_implemented", "message": "vision_locate is a placeholder and is not implemented"}}], safety_notes="Read-only.", implementation_notes="TODO placeholder only. Registry-only until the locator pipeline lands; returns explicit not-implemented semantics instead of a success-shaped payload."))
    registry.register(ToolSpec(name="ui_match", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ui_match, description="Match UI structure with a placeholder interface. TODO: implement structural UIA matching and comparison support.\n\nParameters: none.\nReturns: a placeholder response that explicitly reports the capability as not implemented.\nSafety: read-only.\nExamples: {}.", param_description="No parameters.", result_description="Returns a placeholder response with compatible data fields plus explicit TODO/not-implemented semantics.", input_examples=[{}], output_examples=[{"ok": False, "tool": "ui_match", "message": "ui_match is a placeholder and is not implemented", "data": {"status": "placeholder", "state": "not_implemented", "implemented": False, "available": False, "mode": "match", "source": "registry-only", "capability": "ui_match"}, "error": {"code": "not_implemented", "message": "ui_match is a placeholder and is not implemented"}}], safety_notes="Read-only.", implementation_notes="TODO placeholder only. Registry-only until UI matching lands; returns explicit not-implemented semantics instead of a success-shaped payload."))
