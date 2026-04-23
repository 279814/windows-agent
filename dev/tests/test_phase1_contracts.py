from __future__ import annotations

from desktop_agent_dev.contracts import MotionActionData, MotionEventData, MotionExecutorProtocol, MotionOverlayRequest, MotionPlanRequest, MotionResultData, MotionSchedulerProtocol, MotionVerifyRequest, OverlayRendererProtocol
from desktop_agent_dev.motion import MotionAction, MotionPhase, MotionPoint, MotionScheduler, MotionResult, VirtualCursorState
from desktop_agent_dev.overlay import OverlayRenderer


def test_motion_contract_typed_dict_shapes_are_importable() -> None:
    plan_request: MotionPlanRequest = {
        "kind": "drag",
        "start": (10, 10),
        "end": (100, 100),
        "duration_ms": 180,
        "steps": 12,
        "hover_ms": 20,
        "jitter_px": 2,
        "accel": 1.0,
        "decel": 1.0,
        "task_id": "task-1",
        "action_id": "act-1",
    }
    verify_request: MotionVerifyRequest = {
        "task_id": "task-1",
        "expected_phase": "verified",
        "allow_retry": True,
    }
    overlay_request: MotionOverlayRequest = {"phase": "verified", "metadata": {"kind": "drag"}}
    action_data: MotionActionData = {
        "kind": "drag",
        "start": {"x": 10, "y": 10},
        "end": {"x": 100, "y": 100},
    }
    event_data: MotionEventData = {"action_id": "act-1", "kind": "drag", "phase": "verified", "timestamp_ms": 0}
    result_data: MotionResultData = {"ok": True, "phase": "verified", "action": action_data, "path": [{"x": 10, "y": 10, "t": 0.0}], "event": event_data}

    assert plan_request["kind"] == "drag"
    assert verify_request["allow_retry"] is True
    assert overlay_request["phase"] == "verified"
    assert result_data["ok"] is True


def test_motion_protocols_accept_current_implementations() -> None:
    scheduler = MotionScheduler()
    overlay = OverlayRenderer()

    assert isinstance(scheduler, MotionSchedulerProtocol)
    assert isinstance(overlay, OverlayRendererProtocol)


def test_motion_scheduler_state_machine_frozen_flow() -> None:
    scheduler = MotionScheduler(cursor_state=VirtualCursorState())
    action = MotionAction(kind="move", start=MotionPoint(0, 0), end=MotionPoint(10, 10))

    planned = scheduler.plan_result(action)
    executed = scheduler.execute(action)

    assert scheduler.transition_allowed(MotionPhase.PLANNED, MotionPhase.VERIFIED)
    assert not scheduler.transition_allowed(MotionPhase.VERIFIED, MotionPhase.PLANNED)
    assert planned.phase == MotionPhase.PLANNED
    assert executed.phase == MotionPhase.VERIFIED
    assert scheduler.cursor_state.phase == MotionPhase.VERIFIED


def test_motion_result_and_overlay_snapshots_remain_stable() -> None:
    scheduler = MotionScheduler()
    overlay = OverlayRenderer()
    action = scheduler.plan(kind="click", start=(1, 1), end=(5, 5), action_id="task-2")
    result = scheduler.plan_result(action)
    overlay.attach_motion(result.phase.value, {"kind": action.kind, "last_target": {"x": action.end.x, "y": action.end.y}})
    snapshot = overlay.snapshot()

    assert isinstance(result, MotionResult)
    assert result.action.kind == "click"
    assert snapshot.last_action_status == "planned"
    assert snapshot.last_target == {"x": 5, "y": 5}
