from __future__ import annotations

from desktop_agent_dev.motion import MotionAction, MotionPhase, MotionScheduler, MotionPoint


def test_build_path_returns_points() -> None:
    scheduler = MotionScheduler(seed=11)
    action = scheduler.plan(kind="move", start=(0, 0), end=(120, 80))

    path = scheduler.build_path(action, steps=8)

    assert len(path) == 8
    assert isinstance(path[0], MotionPoint)
    assert path[-1].x == 120
    assert path[-1].y == 80


def test_execute_updates_cursor_state_and_metadata() -> None:
    scheduler = MotionScheduler(seed=11, debug_show_points=True, debug_show_target=True)
    action = scheduler.plan(kind="drag", start=(10, 10), end=(50, 70), action_id="drag-1")

    result = scheduler.execute(action, steps=6)

    assert result.ok is True
    assert result.phase is MotionPhase.VERIFIED
    assert scheduler.cursor_state.x == 50
    assert scheduler.cursor_state.y == 70
    assert scheduler.cursor_state.phase is MotionPhase.VERIFIED
    assert result.metadata["verified"] is True
    assert result.metadata["debug_show_points"] is True
    assert "points" in result.metadata
    assert result.event is not None
    assert result.event.as_data()["phase"] == MotionPhase.VERIFIED.value
    assert result.metadata["phase_history"] == ["planned", "animating", "executing", "verifying", "verified"]


def test_transition_allowed_follows_phase_order() -> None:
    scheduler = MotionScheduler()

    assert scheduler.transition_allowed(MotionPhase.PLANNED, MotionPhase.EXECUTING) is True
    assert scheduler.transition_allowed(MotionPhase.VERIFIED, MotionPhase.EXECUTING) is False


def test_execute_cancelled_returns_cancelled_result() -> None:
    scheduler = MotionScheduler()
    action = scheduler.plan(kind="move", start=(0, 0), end=(10, 10))
    action.cancelled = True

    result = scheduler.execute(action, steps=4)

    assert result.ok is False
    assert result.phase is MotionPhase.CANCELLED
    assert result.metadata["cancelled"] is True


def test_execute_streams_points_and_phases_to_callback() -> None:
    scheduler = MotionScheduler(seed=13)
    action = scheduler.plan(kind="move", start=(0, 0), end=(20, 20), action_id="move-1")
    updates: list[dict[str, object]] = []

    scheduler.execute(action, steps=5, on_update=updates.append)

    point_updates = [item for item in updates if item["type"] == "point"]
    phase_updates = [item for item in updates if item["type"] == "phase"]
    assert len(point_updates) == 5
    assert [item["event"]["phase"] for item in phase_updates] == ["planned", "animating", "executing", "verifying", "verified"]


def test_execute_can_cancel_from_user_interrupt_callback() -> None:
    scheduler = MotionScheduler(seed=17)
    action = scheduler.plan(kind="move", start=(0, 0), end=(30, 30), action_id="move-2")

    result = scheduler.execute(action, steps=6, should_cancel=lambda phase, point: "user_takeover" if point is not None and point.x >= 10 else None)

    assert result.ok is False
    assert result.phase is MotionPhase.CANCELLED
    assert result.metadata["cancel_reason"] == "user_takeover"
