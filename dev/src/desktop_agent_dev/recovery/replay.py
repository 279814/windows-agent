from __future__ import annotations

from typing import Any, Mapping

from .checkpoint import RecoverySnapshot
from .models import ReplayDecision, ReplayDecisionResult, TaskCheckpoint, TaskRecoveryRecord


def _context_drift(
    checkpoint: TaskCheckpoint | None,
    current_environment: Mapping[str, Any] | None,
) -> tuple[bool, list[str]]:
    if checkpoint is None or not checkpoint.environment or not current_environment:
        return False, []
    evidence: list[str] = []
    for key in ("window_title", "window_handle", "app_pid", "display_id"):
        expected = checkpoint.environment.get(key)
        actual = current_environment.get(key)
        if expected is not None and actual is not None and expected != actual:
            evidence.append(f"{key} changed from {expected!r} to {actual!r}")
    return bool(evidence), evidence


def decide_replay_action(
    snapshot: RecoverySnapshot,
    *,
    current_environment: Mapping[str, Any] | None = None,
) -> ReplayDecisionResult:
    record = snapshot.record
    checkpoint = snapshot.checkpoint
    if record is None:
        return ReplayDecisionResult(
            decision=ReplayDecision.MANUAL_INTERVENTION_REQUIRED,
            reason="No persisted recovery record is available.",
            confidence=0.1,
            evidence=["task_record_missing"],
        )

    evidence: list[str] = []
    drifted, drift_evidence = _context_drift(checkpoint, current_environment)
    if drifted:
        evidence.extend(drift_evidence)
        return ReplayDecisionResult(
            decision=ReplayDecision.RESUME_WITH_REOBSERVE,
            reason="Observed environment drift requires a fresh perception pass before resuming.",
            confidence=0.8,
            task_id=record.task_id,
            checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
            resume_from_step=record.step_index,
            evidence=evidence,
        )

    if record.last_error:
        evidence.append(f"last_error={record.last_error}")
        if checkpoint and checkpoint.metadata.get("manual_review_required"):
            return ReplayDecisionResult(
                decision=ReplayDecision.MANUAL_INTERVENTION_REQUIRED,
                reason="Checkpoint explicitly requires human review.",
                confidence=0.95,
                task_id=record.task_id,
                checkpoint_id=checkpoint.checkpoint_id,
                resume_from_step=record.step_index,
                evidence=evidence,
            )
        return ReplayDecisionResult(
            decision=ReplayDecision.RESUME_WITH_REOBSERVE,
            reason="Task previously failed; re-observe before attempting the next step.",
            confidence=0.78,
            task_id=record.task_id,
            checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
            resume_from_step=record.step_index,
            evidence=evidence,
        )

    if record.last_verified_step is not None and record.last_verified_step >= record.step_index:
        evidence.append(f"last_verified_step={record.last_verified_step}")
        return ReplayDecisionResult(
            decision=ReplayDecision.RESUME_SAFE,
            reason="Latest verified step covers the stored progress marker.",
            confidence=0.93,
            task_id=record.task_id,
            checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
            resume_from_step=min(record.last_verified_step + 1, len(record.steps)),
            evidence=evidence,
        )

    if record.last_action:
        evidence.append(f"last_action_phase={record.last_action.get('phase')}")
        replay_safe = False
        if checkpoint:
            replay_safe = bool(
                checkpoint.metadata.get("replay_safe")
                or checkpoint.metadata.get("idempotent")
                or checkpoint.metadata.get("action_replay_safe")
            )
        if replay_safe:
            return ReplayDecisionResult(
                decision=ReplayDecision.RESUME_WITH_REPLAY,
                reason="An unfinished action was checkpointed with replay-safe metadata.",
                confidence=0.72,
                task_id=record.task_id,
                checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
                resume_from_step=record.step_index,
                evidence=evidence,
                metadata={"replay_action": record.last_action},
            )
        return ReplayDecisionResult(
            decision=ReplayDecision.MANUAL_INTERVENTION_REQUIRED,
            reason="An unfinished action exists but no replay-safe evidence was stored.",
            confidence=0.88,
            task_id=record.task_id,
            checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
            resume_from_step=record.step_index,
            evidence=evidence,
        )

    evidence.append(f"status={record.status}")
    return ReplayDecisionResult(
        decision=ReplayDecision.RESUME_SAFE,
        reason="No pending action or failure markers were found in persisted state.",
        confidence=0.7,
        task_id=record.task_id,
        checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
        resume_from_step=record.step_index,
        evidence=evidence,
    )
