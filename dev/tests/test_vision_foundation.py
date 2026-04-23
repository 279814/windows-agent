from __future__ import annotations

from io import BytesIO

from PIL import Image

from desktop_agent_dev.perception import DesktopSnapshot, TreeNodeInfo, WindowInfo
from desktop_agent_dev.vision import (
    CaptureStore,
    OCRResult,
    OCRService,
    OCRTextSpan,
    build_capture,
    locate_text,
    match_ui_nodes,
)


def _png_bytes(size: tuple[int, int] = (12, 10), color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_build_capture_crops_and_persists_snapshot(tmp_path) -> None:
    store = CaptureStore(root=tmp_path)
    snapshot = DesktopSnapshot(
        screenshot=_png_bytes(),
        metadata={"source": "test"},
        active_window=WindowInfo(name="Editor"),
    )

    result = build_capture(snapshot=snapshot, region=(2, 1, 8, 7), store=store, metadata={"tag": "crop"})

    assert result.persisted is True
    assert result.image_path is not None
    assert result.image_size == (6, 6)
    assert result.region is not None
    assert result.region.to_bbox() == (2, 1, 8, 7)
    assert result.path() is not None and result.path().exists()
    assert result.metadata["active_window"] == "Editor"
    assert result.metadata["tag"] == "crop"


def test_ocr_service_returns_graceful_unavailable_when_provider_missing(monkeypatch) -> None:
    monkeypatch.setattr("desktop_agent_dev.vision.ocr.detect_ocr_dependencies", lambda: {"pytesseract": False, "rapidocr_onnxruntime": False, "easyocr": False})
    capture = build_capture(screenshot_bytes=_png_bytes(), persist=False, store=CaptureStore())

    result = OCRService().extract_text(capture)

    assert result.available is False
    assert result.error is not None
    assert result.error["code"] == "ocr_unavailable"
    assert result.capture_id == capture.capture_id


def test_locate_text_prefers_ocr_matches_before_metadata() -> None:
    snapshot = DesktopSnapshot(
        active_window=WindowInfo(name="Project Dashboard", bounds=(0, 0, 300, 200)),
        focused_control={"name": "Search", "text": "Search Projects", "bounds": (10, 10, 120, 32), "control_type": "Edit"},
        tree_nodes=[TreeNodeInfo(name="Search Projects", control_type="Edit", bounds=(10, 10, 120, 32))],
    )
    ocr_result = OCRResult(
        available=True,
        capture_id="capture-1",
        provider="fake",
        text="Search Projects",
        spans=[OCRTextSpan(text="Search Projects", confidence=98.0, bounds=(12, 11, 118, 31))],
    )

    result = locate_text("Search Projects", ocr_result=ocr_result, snapshot=snapshot)

    assert result.best is not None
    assert result.best.source == "ocr"
    assert result.best.bounds == (12, 11, 118, 31)
    assert len(result.candidates) >= 2


def test_match_ui_nodes_scores_by_name_and_automation_id() -> None:
    nodes = [
        TreeNodeInfo(name="Cancel", control_type="Button", automation_id="cancel-btn", class_name="Button", role="button", window_title="Dialog"),
        TreeNodeInfo(name="Save", control_type="Button", automation_id="save-btn", class_name="Button", role="button", window_title="Dialog"),
    ]

    result = match_ui_nodes(nodes, name="Save", automation_id="save-btn", control_type="Button")

    assert result.best is not None
    assert result.best.name == "Save"
    assert result.best.automation_id == "save-btn"
    assert result.best.score > 0.7
