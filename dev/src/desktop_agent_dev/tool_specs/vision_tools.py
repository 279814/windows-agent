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

    registry.register(ToolSpec(name="vision_capture", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_capture, description="视觉截图占位接口，用于后续接入图像感知与视觉模型。", param_description="无参数。", result_description="返回视觉捕获占位结果。", input_examples=[{}], output_examples=[{"ok": True, "tool": "vision_capture", "data": {"status": "placeholder", "mode": "capture", "source": "registry-only"}}], safety_notes="只读。", implementation_notes="Registry-only placeholder until vision pipeline lands."))
    registry.register(ToolSpec(name="ocr_extract", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ocr_extract, description="OCR 识别占位接口，用于后续接入文本识别流程。", param_description="无参数。", result_description="返回 OCR 占位结果。", input_examples=[{}], output_examples=[{"ok": True, "tool": "ocr_extract", "data": {"status": "placeholder", "mode": "ocr", "source": "registry-only"}}], safety_notes="只读。", implementation_notes="Registry-only placeholder until OCR pipeline lands."))
    registry.register(ToolSpec(name="vision_locate", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=vision_locate, description="视觉定位占位接口，用于后续接入元素定位与坐标推断。", param_description="无参数。", result_description="返回视觉定位占位结果。", input_examples=[{}], output_examples=[{"ok": True, "tool": "vision_locate", "data": {"status": "placeholder", "mode": "locate", "source": "registry-only"}}], safety_notes="只读。", implementation_notes="Registry-only placeholder until locator pipeline lands."))
    registry.register(ToolSpec(name="ui_match", kind="snapshot", params_schema={"type": "object", "properties": {}, "required": []}, result_schema=RESULT_SCHEMAS["default"], permission=None, executor=ui_match, description="UI 结构匹配占位接口，用于后续接入 UIA 结构比对。", param_description="无参数。", result_description="返回 UI 匹配占位结果。", input_examples=[{}], output_examples=[{"ok": True, "tool": "ui_match", "data": {"status": "placeholder", "mode": "match", "source": "registry-only"}}], safety_notes="只读。", implementation_notes="Registry-only placeholder until UI matching lands."))
