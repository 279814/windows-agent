from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    type: str
    payload: dict[str, Any]
    source_tool: str | None = None
    source_app: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArtifactStore:
    def __init__(self) -> None:
        self._records: dict[str, ArtifactRecord] = {}

    def create(self, *, type: str, payload: dict[str, Any], source_tool: str | None = None, source_app: str | None = None) -> ArtifactRecord:
        record = ArtifactRecord(
            artifact_id=f"artifact-{uuid4().hex[:12]}",
            type=type,
            payload=payload,
            source_tool=source_tool,
            source_app=source_app,
        )
        self._records[record.artifact_id] = record
        return record

    def get(self, artifact_id: str) -> ArtifactRecord | None:
        return self._records.get(artifact_id)

    def list(self) -> list[ArtifactRecord]:
        return list(self._records.values())
