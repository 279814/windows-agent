from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .artifacts import ArtifactRecord, ArtifactStore


class WorkflowBridge:
    """Small helper for turning observations into reusable workflow artifacts."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def from_snapshot(self, snapshot: Any, *, source_tool: str = "desktop_snapshot", source_app: str | None = None) -> ArtifactRecord:
        payload = {
            "active_window": None if getattr(snapshot, "active_window", None) is None else asdict(snapshot.active_window),
            "focused_control": getattr(snapshot, "focused_control", None),
            "metadata": dict(getattr(snapshot, "metadata", {}) or {}),
        }
        return self.artifact_store.create(type="window_ref", payload=payload, source_tool=source_tool, source_app=source_app)

    def from_text(self, text: str, *, source_tool: str, source_app: str | None = None, metadata: dict[str, Any] | None = None) -> ArtifactRecord:
        payload = {"text": text, "metadata": dict(metadata or {})}
        return self.artifact_store.create(type="text", payload=payload, source_tool=source_tool, source_app=source_app)

    def from_file(self, path: str, *, source_tool: str, source_app: str | None = None, metadata: dict[str, Any] | None = None) -> ArtifactRecord:
        payload = {"path": path, "metadata": dict(metadata or {})}
        return self.artifact_store.create(type="file", payload=payload, source_tool=source_tool, source_app=source_app)
