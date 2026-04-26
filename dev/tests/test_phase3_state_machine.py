from __future__ import annotations

from desktop_agent_dev.executor import Executor
from desktop_agent_dev.motion import MotionAction, MotionPhase, MotionPoint, MotionScheduler, VirtualCursorState
from desktop_agent_dev.state import TaskStore


class FailingScheduler(MotionScheduler):
    def execute(self, action, steps: int = 16):
        raise RuntimeError("boom")


def test_task_store_transitions_and_retry_tracking() -> None:
    store = TaskStore()
    record = store.upsert_plan("task-1", "goal", [{"step_index": 0, "name": "observe"}])
    assert record.status == "planned"

    store.advance("task-1", action={"phase": MotionPhase.PLANNED.value}, verified=False)
    assert store.get("task-1").status == "executing"

    store.advance("task-1", verified=True)
    assert store.get("task-1").status == "verified"

    store.advance("task-1", error_message="timeout")
    assert store.get("task-1").status == "failed"
    assert store.get("task-1").retries == 1


def test_motion_scheduler_cancel_and_state_flow() -> None:
    scheduler = MotionScheduler(cursor_state=VirtualCursorState())
    action = MotionAction(kind="move", start=MotionPoint(0, 0), end=MotionPoint(10, 10), cancelled=True)
    result = scheduler.execute(action)

    assert result.phase == MotionPhase.CANCELLED
    assert scheduler.cursor_state.phase == MotionPhase.CANCELLED
    assert "cancelled" in result.metadata["phase_history"]


def test_executor_records_failure_for_retry_and_timeout_paths() -> None:
    executor = Executor(motion_scheduler=FailingScheduler())
    result = executor.motion_execute("move", (0, 0), (10, 10), task_id="task-2")

    assert result["ok"] is False
    assert result["phase"] == MotionPhase.FAILED.value
    assert result["task_state"] == "failed"
