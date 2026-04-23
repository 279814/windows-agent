from __future__ import annotations

from desktop_agent_dev.recovery import (
    RecoveryStore,
    ReplayDecision,
    TaskRecoveryRecord,
    decide_replay_action,
    load_recovery_snapshot,
    save_checkpoint,
)
from desktop_agent_dev.state import TaskRecord


def test_recovery_store_persists_task_and_checkpoint(tmp_path) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    record = TaskRecord(
        task_id="task-1",
        goal="open notepad",
        steps=[{"name": "observe"}, {"name": "click"}],
        step_index=1,
        status="executing",
        last_action={"tool": "click", "phase": "running"},
    )

    checkpoint = save_checkpoint(
        store,
        record,
        reason="before_click",
        phase="running",
        environment={"window_title": "Untitled - Notepad", "display_id": "primary"},
        metadata={"replay_safe": True},
    )

    snapshot = load_recovery_snapshot(store, "task-1")
    assert snapshot.record is not None
    assert snapshot.checkpoint is not None
    assert snapshot.record.goal == "open notepad"
    assert snapshot.record.last_action == {"tool": "click", "phase": "running"}
    assert snapshot.checkpoint.checkpoint_id == checkpoint.checkpoint_id
    assert snapshot.checkpoint.environment["window_title"] == "Untitled - Notepad"


def test_replay_decision_returns_resume_safe_after_verified_step(tmp_path) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    record = TaskRecoveryRecord(
        task_id="task-2",
        goal="verify",
        steps=[{"name": "observe"}, {"name": "verify"}],
        step_index=1,
        status="verified",
        last_verified_step=1,
    )
    save_checkpoint(store, record, reason="verified")

    decision = decide_replay_action(load_recovery_snapshot(store, "task-2"))
    assert decision.decision == ReplayDecision.RESUME_SAFE
    assert decision.resume_from_step == 2


def test_replay_decision_reobserves_on_environment_drift(tmp_path) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    record = TaskRecoveryRecord(
        task_id="task-3",
        goal="switch window",
        steps=[{"name": "focus"}],
        step_index=0,
        status="executing",
    )
    save_checkpoint(
        store,
        record,
        reason="focused",
        environment={"window_title": "Calculator", "display_id": "primary"},
    )

    decision = decide_replay_action(
        load_recovery_snapshot(store, "task-3"),
        current_environment={"window_title": "Settings", "display_id": "primary"},
    )
    assert decision.decision == ReplayDecision.RESUME_WITH_REOBSERVE
    assert any("window_title changed" in item for item in decision.evidence)


def test_replay_decision_prefers_replay_for_idempotent_inflight_action(tmp_path) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    record = TaskRecoveryRecord(
        task_id="task-4",
        goal="click save",
        steps=[{"name": "click"}],
        step_index=0,
        status="executing",
        last_action={"tool": "click", "target": "save_button", "phase": "running"},
    )
    save_checkpoint(store, record, reason="before_click", metadata={"idempotent": True})

    decision = decide_replay_action(load_recovery_snapshot(store, "task-4"))
    assert decision.decision == ReplayDecision.RESUME_WITH_REPLAY
    assert decision.metadata["replay_action"]["tool"] == "click"


def test_replay_decision_requires_manual_review_for_non_replayable_action(tmp_path) -> None:
    store = RecoveryStore(tmp_path / "recovery")
    record = TaskRecoveryRecord(
        task_id="task-5",
        goal="submit payment",
        steps=[{"name": "submit"}],
        step_index=0,
        status="executing",
        last_action={"tool": "click", "target": "confirm_payment", "phase": "running"},
    )
    save_checkpoint(store, record, reason="before_submit")

    decision = decide_replay_action(load_recovery_snapshot(store, "task-5"))
    assert decision.decision == ReplayDecision.MANUAL_INTERVENTION_REQUIRED
