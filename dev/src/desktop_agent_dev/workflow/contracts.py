from __future__ import annotations

from typing import Any, Literal, TypedDict


ArtifactType = Literal["text", "file", "table", "image", "window_ref", "ocr", "capture", "generic"]
WorkflowStepKind = Literal["observe", "extract", "switch_window", "input", "verify", "artifact"]


class WorkflowStep(TypedDict, total=False):
    kind: WorkflowStepKind
    name: str
    description: str
    params: dict[str, Any]


class WorkflowRequest(TypedDict, total=False):
    workflow_id: str
    goal: str
    source_app: str
    target_app: str
    steps: list[WorkflowStep]
    metadata: dict[str, Any]
