from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from .motion import MotionAction, MotionEvent, MotionPhase, MotionResult, MotionPoint, VirtualCursorState


class MotionPointData(TypedDict, total=False):
    x: int
    y: int
    t: float | None


class MotionActionData(TypedDict, total=False):
    kind: str
    start: MotionPointData
    end: MotionPointData
    duration_ms: int
    easing: str
    metadata: dict[str, Any]
    hover_ms: int
    jitter_px: int
    accel: float
    decel: float
    action_id: str
    cancelled: bool


class MotionEventData(TypedDict, total=False):
    action_id: str
    kind: str
    phase: str
    timestamp_ms: int
    detail: str
    metadata: dict[str, Any]


class MotionResultData(TypedDict, total=False):
    ok: bool
    phase: str
    action: MotionActionData
    path: list[MotionPointData]
    detail: str
    metadata: dict[str, Any]
    event: MotionEventData


class OverlaySnapshotData(TypedDict, total=False):
    visible: bool
    cursor_x: int
    cursor_y: int
    cursor_color: str
    user_cursor_color: str
    cursor_size: int
    user_cursor_size: int
    persistent: bool
    trail: list[tuple[int, int]]
    metadata: dict[str, Any]
    last_action_kind: str | None
    last_action_status: str | None
    last_target: dict[str, int] | None
    last_error: str | None
    last_verified_at: str | None
    display_id: str | None
    scale_factor: float
    monitor_bounds: list[dict[str, int]]
    transition_state: str | None
    transition_reason: str | None
    interruption_state: str | None
    window_state: str | None


class MotionPlanRequest(TypedDict, total=False):
    kind: str
    start: tuple[int, int]
    end: tuple[int, int]
    duration_ms: int
    steps: int
    hover_ms: int
    jitter_px: int
    accel: float
    decel: float
    task_id: str
    action_id: str


class MotionExecutionRequest(MotionPlanRequest, total=False):
    pass


class MotionVerifyRequest(TypedDict, total=False):
    task_id: str
    action: MotionActionData
    expected_phase: str
    expected_target: MotionPointData
    allow_retry: bool


class MotionOverlayRequest(TypedDict, total=False):
    phase: str
    metadata: dict[str, Any]


@runtime_checkable
class MotionSchedulerProtocol(Protocol):
    cursor_state: VirtualCursorState

    def build_path(self, action: MotionAction, steps: int = 16) -> list[MotionPoint]:
        ...

    def plan(self, *, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, metadata: dict[str, Any] | None = None, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, action_id: str | None = None) -> MotionAction:
        ...

    def plan_result(self, action: MotionAction, steps: int = 16) -> MotionResult:
        ...

    def execute(self, action: MotionAction, steps: int = 16) -> MotionResult:
        ...

    def run(self, action: MotionAction, steps: int = 16) -> MotionResult:
        ...


@runtime_checkable
class OverlayRendererProtocol(Protocol):
    def show(self) -> None:
        ...

    def hide(self) -> None:
        ...

    def update_cursor(self, x: int, y: int) -> None:
        ...

    def attach_motion(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
        ...

    def snapshot(self) -> Any:
        ...


@runtime_checkable
class MotionVerifierProtocol(Protocol):
    def verify(self, request: MotionVerifyRequest) -> MotionResultData:
        ...


@runtime_checkable
class MotionExecutorProtocol(Protocol):
    def motion_preview(self, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, steps: int = 16, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, task_id: str | None = None) -> dict[str, Any]:
        ...

    def motion_execute(self, kind: str, start: tuple[int, int], end: tuple[int, int], duration_ms: int | None = None, steps: int = 16, hover_ms: int = 0, jitter_px: int = 0, accel: float = 1.0, decel: float = 1.0, task_id: str | None = None) -> dict[str, Any]:
        ...

    def verify_motion(self, request: MotionVerifyRequest) -> dict[str, Any]:
        ...
