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

    specs = [
        ("vision_capture", {"type": "object", "properties": {}, "required": []}, vision_capture, "视觉截图占位接口。"),
        ("ocr_extract", {"type": "object", "properties": {}, "required": []}, ocr_extract, "OCR 识别占位接口。"),
        ("vision_locate", {"type": "object", "properties": {}, "required": []}, vision_locate, "视觉定位占位接口。"),
        ("ui_match", {"type": "object", "properties": {}, "required": []}, ui_match, "UI 结构匹配占位接口。"),
    ]
    for name, params_schema, executor, description in specs:
        registry.register(
            ToolSpec(
                name=name,
                kind="snapshot",
                params_schema=params_schema,
                result_schema=RESULT_SCHEMAS["default"],
                permission=None,
                executor=executor,
                description=description,
                examples=[{}],
            )
        )
