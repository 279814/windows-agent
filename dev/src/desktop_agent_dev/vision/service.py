from __future__ import annotations

from pathlib import Path
from typing import Any

from ..perception import DesktopSnapshot
from .cache import CaptureStore, default_capture_root
from .capture import build_capture
from .locate import locate_text
from .models import CaptureRegion, CaptureResult, LocateResult, OCRResult, UIMatchResult
from .ocr import OCRService
from .ui_match import match_snapshot_ui


class VisionService:
    """Integration-friendly façade for Phase 2 vision capabilities."""

    def __init__(self, capture_root: str | Path | None = None, *, preferred_ocr_provider: str = "pytesseract") -> None:
        self.capture_store = CaptureStore(Path(capture_root) if capture_root else default_capture_root())
        self.ocr_service = OCRService(preferred_provider=preferred_ocr_provider)

    def capture(
        self,
        *,
        snapshot: DesktopSnapshot,
        region: CaptureRegion | tuple[int, int, int, int] | dict[str, Any] | None = None,
        persist: bool = True,
        source: str = "perception",
        metadata: dict[str, Any] | None = None,
    ) -> CaptureResult:
        return build_capture(
            snapshot=snapshot,
            region=region,
            persist=persist,
            source=source,
            metadata=metadata,
            store=self.capture_store,
        )

    def resolve_capture(self, capture_id: str) -> CaptureResult | None:
        path = self.capture_store.resolve(capture_id)
        if path is None:
            return None
        return CaptureResult(
            capture_id=capture_id,
            image_path=str(path),
            image_bytes=path.read_bytes(),
            image_format="PNG",
            source="capture_store",
            persisted=True,
            metadata={"resolved": True},
        )

    def ocr_extract(
        self,
        *,
        capture: CaptureResult,
        language: str | None = None,
    ) -> OCRResult:
        return self.ocr_service.extract_text(capture, language=language)

    def locate(
        self,
        query: str,
        *,
        ocr_result: OCRResult | None = None,
        snapshot: DesktopSnapshot | None = None,
        min_score: float = 0.5,
    ) -> LocateResult:
        return locate_text(query, ocr_result=ocr_result, snapshot=snapshot, min_score=min_score)

    def ui_match(
        self,
        *,
        snapshot: DesktopSnapshot,
        name: str | None = None,
        control_type: str | None = None,
        automation_id: str | None = None,
        class_name: str | None = None,
        role: str | None = None,
        window_title: str | None = None,
        min_score: float = 0.5,
    ) -> UIMatchResult:
        return match_snapshot_ui(
            snapshot,
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            class_name=class_name,
            role=role,
            window_title=window_title,
            min_score=min_score,
        )
