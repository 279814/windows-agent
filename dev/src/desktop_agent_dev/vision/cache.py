from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from os import getpid
from pathlib import Path


_CAPTURE_COUNTER = count(1)


def default_capture_root() -> Path:
    return Path(__file__).resolve().parents[3] / "tmp" / "captures"


class CaptureStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_capture_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def new_capture_id(self, prefix: str = "capture") -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        return f"{prefix}-{stamp}-{getpid():x}-{next(_CAPTURE_COUNTER):04d}"

    def path_for(self, capture_id: str, suffix: str = ".png") -> Path:
        return self.root / f"{capture_id}{suffix}"

    def persist_bytes(self, payload: bytes, *, capture_id: str, suffix: str = ".png") -> Path:
        path = self.path_for(capture_id, suffix=suffix)
        path.write_bytes(payload)
        return path

    def resolve(self, capture_id: str, suffix: str = ".png") -> Path | None:
        path = self.path_for(capture_id, suffix=suffix)
        return path if path.exists() else None
