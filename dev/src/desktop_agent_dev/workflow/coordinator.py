from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .artifacts import ArtifactRecord, ArtifactStore
from .bridge import WorkflowBridge
from .contracts import WorkflowRequest


@dataclass(slots=True)
class WorkflowResult:
    ok: bool
    workflow_id: str
    status: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    message: str = "ok"


class WorkflowCoordinator:
    """Phase 2 cross-application workflow skeleton."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()
        self.bridge = WorkflowBridge(self.artifact_store)

    def plan(self, request: WorkflowRequest) -> WorkflowResult:
        workflow_id = request.get("workflow_id") or f"workflow-{abs(hash(request.get('goal', ''))) & 0xFFFF_FFFF:x}"
        steps = []
        for index, step in enumerate(request.get("steps", [])):
            steps.append(
                {
                    "step_index": index,
                    "kind": step.get("kind"),
                    "name": step.get("name"),
                    "description": step.get("description"),
                    "params": dict(step.get("params", {}) or {}),
                }
            )
        return WorkflowResult(
            ok=True,
            workflow_id=workflow_id,
            status="planned",
            steps=steps,
            artifacts=self.artifact_store.list(),
            message="workflow planned",
        )
