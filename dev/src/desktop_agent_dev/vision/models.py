from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


Bounds = tuple[int, int, int, int]


@dataclass(slots=True, frozen=True)
class CaptureRegion:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def is_empty(self) -> bool:
        return self.width == 0 or self.height == 0

    def to_bbox(self) -> Bounds:
        return (self.left, self.top, self.right, self.bottom)

    def clamp(self, size: tuple[int, int]) -> "CaptureRegion":
        width, height = size
        left = min(max(self.left, 0), width)
        top = min(max(self.top, 0), height)
        right = min(max(self.right, left), width)
        bottom = min(max(self.bottom, top), height)
        return CaptureRegion(left=left, top=top, right=right, bottom=bottom)

    @classmethod
    def from_value(cls, value: "CaptureRegion | Bounds | Mapping[str, Any] | None") -> "CaptureRegion | None":
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, tuple) and len(value) == 4:
            left, top, right, bottom = value
            return cls(int(left), int(top), int(right), int(bottom))
        if isinstance(value, Mapping):
            if {"left", "top", "right", "bottom"} <= set(value):
                return cls(
                    int(value["left"]),
                    int(value["top"]),
                    int(value["right"]),
                    int(value["bottom"]),
                )
            if {"x", "y", "width", "height"} <= set(value):
                x = int(value["x"])
                y = int(value["y"])
                width = int(value["width"])
                height = int(value["height"])
                return cls(x, y, x + width, y + height)
        raise TypeError(f"Unsupported capture region value: {value!r}")


@dataclass(slots=True)
class CaptureResult:
    capture_id: str
    image_path: str | None = None
    image_bytes: bytes | None = None
    image_format: str = "PNG"
    image_size: tuple[int, int] | None = None
    region: CaptureRegion | None = None
    source: str = "vision"
    persisted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def path(self) -> Path | None:
        return Path(self.image_path) if self.image_path else None


@dataclass(slots=True, frozen=True)
class OCRTextSpan:
    text: str
    confidence: float | None = None
    bounds: Bounds | None = None
    line_index: int | None = None
    block_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OCRResult:
    available: bool
    capture_id: str | None = None
    provider: str | None = None
    text: str = ""
    spans: list[OCRTextSpan] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    @classmethod
    def unavailable(
        cls,
        *,
        capture_id: str | None,
        provider: str | None = None,
        message: str,
        code: str = "ocr_unavailable",
        metadata: Mapping[str, Any] | None = None,
    ) -> "OCRResult":
        return cls(
            available=False,
            capture_id=capture_id,
            provider=provider,
            metadata=dict(metadata or {}),
            error={"code": code, "message": message},
        )


@dataclass(slots=True, frozen=True)
class LocateCandidate:
    text: str
    score: float
    source: str
    bounds: Bounds | None = None
    capture_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LocateResult:
    query: str
    strategy: str
    candidates: list[LocateCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def best(self) -> LocateCandidate | None:
        return self.candidates[0] if self.candidates else None


@dataclass(slots=True, frozen=True)
class UIMatchCandidate:
    node_index: int
    score: float
    reasons: tuple[str, ...]
    name: str
    control_type: str
    automation_id: str | None = None
    class_name: str | None = None
    role: str | None = None
    window_title: str | None = None
    bounds: Bounds | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UIMatchResult:
    candidates: list[UIMatchCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def best(self) -> UIMatchCandidate | None:
        return self.candidates[0] if self.candidates else None
