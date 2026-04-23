from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from .checkpoint import load_recovery_snapshot, save_checkpoint
from .models import ReplayDecisionResult, TaskRecoveryRecord
from .replay import decide_replay_action
from .store import RecoveryStore


class RecoveryService:
    """High-level façade for persistent task records and replay decisions."""

    def __init__(self, root: str | Path | None = None) -> None:
        base_root = Path(root) if root else Path(__file__).resolve().parents[3] / "tmp" / "recovery"
        self.store = RecoveryStore(base_root)

    def sync_task(self, record: Any, *, metadata: Mapping[str, Any] | None = None) -> TaskRecoveryRecord:
        recovery_record = record if isinstance(record, TaskRecoveryRecord) else TaskRecoveryRecord.from_task_record(record, metadata=metadata)
        self.store.save_task(recovery_record)
        return recovery_record

    def load_task(self, task_id: str) -> TaskRecoveryRecord | None:
        return self.store.load_task(task_id)

    def save_checkpoint(
        self,
        task_record: Any,
        *,
        reason: str,
        phase: str | None = None,
        environment: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ):
        return save_checkpoint(
            self.store,
            task_record,
            reason=reason,
            phase=phase,
            environment=environment,
            metadata=metadata,
        )

    def load_snapshot(self, task_id: str):
        return load_recovery_snapshot(self.store, task_id)

    def decide_resume(self, task_id: str, *, current_environment: Mapping[str, Any] | None = None) -> ReplayDecisionResult:
        snapshot = self.load_snapshot(task_id)
        return decide_replay_action(snapshot, current_environment=current_environment)

    @staticmethod
    def record_payload(record: Any) -> dict[str, Any]:
        if isinstance(record, TaskRecoveryRecord):
            return record.to_dict()
        if is_dataclass(record):
            return asdict(record)
        if hasattr(record, "__dict__"):
            return dict(record.__dict__)
        return {}
