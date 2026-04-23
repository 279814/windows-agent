from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from ..perception import DesktopSnapshot
from .cache import CaptureStore
from .models import CaptureRegion, CaptureResult


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _load_image(*, screenshot_bytes: bytes | None, screenshot_path: str | Path | None) -> tuple[Image.Image, bytes]:
    if screenshot_bytes is not None:
        payload = screenshot_bytes
        image = Image.open(BytesIO(payload))
        image.load()
        return image, payload

    if screenshot_path is None:
        raise ValueError("Screenshot bytes or screenshot path is required for vision capture")

    payload = Path(screenshot_path).read_bytes()
    image = Image.open(BytesIO(payload))
    image.load()
    return image, payload


def _snapshot_metadata(snapshot: DesktopSnapshot | None) -> dict[str, Any]:
    if snapshot is None:
        return {}
    metadata = dict(snapshot.metadata)
    metadata.setdefault("active_window", snapshot.active_window.name if snapshot.active_window else None)
    metadata.setdefault("tree_node_count", len(snapshot.tree_nodes))
    metadata.setdefault("cursor", snapshot.cursor)
    metadata.setdefault("focused_control", snapshot.focused_control)
    return metadata


def build_capture(
    *,
    snapshot: DesktopSnapshot | None = None,
    screenshot_bytes: bytes | None = None,
    screenshot_path: str | Path | None = None,
    region: CaptureRegion | tuple[int, int, int, int] | dict[str, Any] | None = None,
    persist: bool = True,
    source: str = "perception",
    metadata: dict[str, Any] | None = None,
    store: CaptureStore | None = None,
) -> CaptureResult:
    store = store or CaptureStore()
    capture_id = store.new_capture_id()

    if screenshot_bytes is None and snapshot is not None:
        screenshot_bytes = snapshot.screenshot
    if screenshot_path is None and snapshot is not None:
        screenshot_path = snapshot.screenshot_path

    image, _ = _load_image(screenshot_bytes=screenshot_bytes, screenshot_path=screenshot_path)
    original_size = image.size
    normalized_region = CaptureRegion.from_value(region)
    if normalized_region is not None:
        normalized_region = normalized_region.clamp(original_size)
        if normalized_region.is_empty:
            raise ValueError("Capture region is empty after clamping to screenshot bounds")
        image = image.crop(normalized_region.to_bbox())

    encoded = _image_to_png_bytes(image)
    image_path = None
    if persist:
        image_path = str(store.persist_bytes(encoded, capture_id=capture_id, suffix=".png"))

    merged_metadata = _snapshot_metadata(snapshot)
    if metadata:
        merged_metadata.update(metadata)
    merged_metadata.update(
        {
            "original_size": original_size,
            "captured_size": image.size,
            "crop_applied": normalized_region is not None,
            "capture_source": source,
        }
    )
    if screenshot_path is not None:
        merged_metadata.setdefault("upstream_screenshot_path", str(screenshot_path))

    return CaptureResult(
        capture_id=capture_id,
        image_path=image_path,
        image_bytes=encoded,
        image_format="PNG",
        image_size=image.size,
        region=normalized_region,
        source=source,
        persisted=persist,
        metadata=merged_metadata,
    )
