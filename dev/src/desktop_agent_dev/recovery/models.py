from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clone_jsonish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clone_jsonish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_jsonish(item) for item in value]
    if isinstance(value, tuple):
        return [_clone_jsonish(item) for item in value]
    return value


def _to_mapping(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if is_dataclass(record):
        return asdict(record)
    output: dict[str, Any] = {}
    for name in (
        "task_id",
        "goal",
        "steps",
        "step_index",
        "retries",
        "observations",
        "status",
        "last_action",
        "last_error",
        "last_verified_step",
    ):
        if hasattr(record, name):
            output[name] = getattr(record, name)
    return output


@dataclass(slots=True)
class TaskRecoveryRecord:
    task_id: str
    goal: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    step_index: int = 0
    retries: int = 0
    observations: list[str] = field(default_factory=list)
    status: str = "planned"
    last_action: dict[str, Any] | None = None
    last_error: str | None = None
    last_verified_step: int | None = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task_record(
        cls,
        record: Any,
        *,
        metadata: Mapping[str, Any] | None = None,
        updated_at: str | None = None,
    ) -> TaskRecoveryRecord:
        payload = _to_mapping(record)
        return cls(
            task_id=str(payload.get("task_id", "")),
            goal=str(payload.get("goal", "")),
            steps=[dict(step) for step in payload.get("steps", [])],
            step_index=int(payload.get("step_index", 0)),
            retries=int(payload.get("retries", 0)),
            observations=[str(item) for item in payload.get("observations", [])],
            status=str(payload.get("status", "planned")),
            last_action=_clone_jsonish(payload.get("last_action")),
            last_error=None if payload.get("last_error") is None else str(payload.get("last_error")),
            last_verified_step=payload.get("last_verified_step"),
            updated_at=updated_at or _utc_now_iso(),
            metadata=_clone_jsonish(dict(metadata or {})),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TaskRecoveryRecord:
        known = {item.name for item in fields(cls)}
        data = {key: value for key, value in payload.items() if key in known}
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskCheckpoint:
    task_id: str
    checkpoint_id: str
    created_at: str = field(default_factory=_utc_now_iso)
    step_index: int = 0
    status: str = "planned"
    reason: str = "unspecified"
    phase: str | None = None
    last_action: dict[str, Any] | None = None
    last_error: str | None = None
    last_verified_step: int | None = None
    observations: list[str] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TaskCheckpoint:
        known = {item.name for item in fields(cls)}
        data = {key: value for key, value in payload.items() if key in known}
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReplayDecision(StrEnum):
    RESUME_SAFE = "resume_safe"
    RESUME_WITH_REOBSERVE = "resume_with_reobserve"
    RESUME_WITH_REPLAY = "resume_with_replay"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


@dataclass(slots=True)
class ReplayDecisionResult:
    decision: ReplayDecision
    reason: str
    confidence: float
    task_id: str | None = None
    checkpoint_id: str | None = None
    resume_from_step: int | None = None
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload
