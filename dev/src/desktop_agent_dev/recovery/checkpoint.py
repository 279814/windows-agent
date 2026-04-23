from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from typing import Any, Mapping

from .models import TaskCheckpoint, TaskRecoveryRecord
from .store import RecoveryStore


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _checkpoint_id(task_id: str, step_index: int, reason: str, created_at: str) -> str:
    digest = sha1(f"{task_id}:{step_index}:{reason}:{created_at}".encode("utf-8")).hexdigest()
    return digest[:12]


def build_checkpoint(
    task_record: Any,
    *,
    reason: str,
    phase: str | None = None,
    environment: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> TaskCheckpoint:
    recovery_record = (
        task_record if isinstance(task_record, TaskRecoveryRecord) else TaskRecoveryRecord.from_task_record(task_record)
    )
    created = created_at or _utc_now_iso()
    return TaskCheckpoint(
        task_id=recovery_record.task_id,
        checkpoint_id=_checkpoint_id(recovery_record.task_id, recovery_record.step_index, reason, created),
        created_at=created,
        step_index=recovery_record.step_index,
        status=recovery_record.status,
        reason=reason,
        phase=phase,
        last_action=None if recovery_record.last_action is None else dict(recovery_record.last_action),
        last_error=recovery_record.last_error,
        last_verified_step=recovery_record.last_verified_step,
        observations=list(recovery_record.observations),
        environment=dict(environment or {}),
        metadata={**recovery_record.metadata, **dict(metadata or {})},
    )


@dataclass(slots=True)
class RecoverySnapshot:
    record: TaskRecoveryRecord | None
    checkpoint: TaskCheckpoint | None


def save_checkpoint(
    store: RecoveryStore,
    task_record: Any,
    *,
    reason: str,
    phase: str | None = None,
    environment: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    updated_at: str | None = None,
) -> TaskCheckpoint:
    recovery_record = (
        task_record
        if isinstance(task_record, TaskRecoveryRecord)
        else TaskRecoveryRecord.from_task_record(task_record, metadata=metadata, updated_at=updated_at)
    )
    recovery_record.updated_at = updated_at or recovery_record.updated_at or _utc_now_iso()
    store.save_task(recovery_record)
    checkpoint = build_checkpoint(
        recovery_record,
        reason=reason,
        phase=phase,
        environment=environment,
        metadata=metadata,
        created_at=recovery_record.updated_at,
    )
    store.append_checkpoint(checkpoint)
    return checkpoint


def load_recovery_snapshot(store: RecoveryStore, task_id: str) -> RecoverySnapshot:
    return RecoverySnapshot(
        record=store.load_task(task_id),
        checkpoint=store.load_latest_checkpoint(task_id),
    )
