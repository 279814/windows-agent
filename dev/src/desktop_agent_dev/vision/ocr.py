from __future__ import annotations

from importlib.util import find_spec
from io import BytesIO
from pathlib import Path

from PIL import Image

from .models import CaptureResult, OCRResult, OCRTextSpan


def detect_ocr_dependencies() -> dict[str, bool]:
    return {
        "pytesseract": find_spec("pytesseract") is not None,
        "rapidocr_onnxruntime": find_spec("rapidocr_onnxruntime") is not None,
        "easyocr": find_spec("easyocr") is not None,
    }


def _load_capture_image(capture: CaptureResult) -> Image.Image:
    if capture.image_bytes is not None:
        image = Image.open(BytesIO(capture.image_bytes))
        image.load()
        return image
    if capture.image_path:
        image = Image.open(Path(capture.image_path))
        image.load()
        return image
    raise ValueError("Capture result does not include image bytes or image path")


class OCRService:
    def __init__(self, preferred_provider: str = "pytesseract") -> None:
        self.preferred_provider = preferred_provider

    def extract_text(self, capture: CaptureResult, *, language: str | None = None) -> OCRResult:
        deps = detect_ocr_dependencies()
        metadata = {"dependencies": deps, "preferred_provider": self.preferred_provider}
        if not deps.get(self.preferred_provider, False):
            return OCRResult.unavailable(
                capture_id=capture.capture_id,
                provider=self.preferred_provider,
                message=f"OCR provider '{self.preferred_provider}' is not installed",
                metadata=metadata,
            )

        if self.preferred_provider != "pytesseract":
            return OCRResult.unavailable(
                capture_id=capture.capture_id,
                provider=self.preferred_provider,
                message=f"OCR provider '{self.preferred_provider}' is detected but not wired yet",
                code="ocr_provider_not_wired",
                metadata=metadata,
            )

        try:
            import pytesseract
            from pytesseract import Output
        except Exception as exc:
            return OCRResult.unavailable(
                capture_id=capture.capture_id,
                provider="pytesseract",
                message=f"Failed to import pytesseract: {exc}",
                code="ocr_import_failed",
                metadata=metadata,
            )

        try:
            image = _load_capture_image(capture)
            data = pytesseract.image_to_data(image, lang=language, output_type=Output.DICT)
        except Exception as exc:
            return OCRResult.unavailable(
                capture_id=capture.capture_id,
                provider="pytesseract",
                message=f"OCR extraction failed: {exc}",
                code="ocr_failed",
                metadata=metadata,
            )

        spans: list[OCRTextSpan] = []
        fragments: list[str] = []
        total = len(data.get("text", []))
        for index in range(total):
            text = (data["text"][index] or "").strip()
            if not text:
                continue
            left = int(data["left"][index])
            top = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])
            confidence_raw = data["conf"][index]
            confidence = None
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = None
            fragments.append(text)
            spans.append(
                OCRTextSpan(
                    text=text,
                    confidence=confidence,
                    bounds=(left, top, left + width, top + height),
                    line_index=int(data.get("line_num", [0] * total)[index]),
                    block_index=int(data.get("block_num", [0] * total)[index]),
                )
            )

        metadata["span_count"] = len(spans)
        return OCRResult(
            available=True,
            capture_id=capture.capture_id,
            provider="pytesseract",
            text=" ".join(fragments).strip(),
            spans=spans,
            metadata=metadata,
        )
