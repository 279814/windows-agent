"""Desktop agent dev workspace package."""

from .motion import MotionAction, MotionPhase, MotionPoint, MotionResult, MotionScheduler, VirtualCursorState
from .orchestrator import DesktopOrchestrator, OrchestrationResult
from .overlay import OverlayFrame, OverlayRenderer

__all__ = [
    "__version__",
    "MotionAction",
    "MotionPhase",
    "MotionPoint",
    "MotionResult",
    "MotionScheduler",
    "VirtualCursorState",
    "DesktopOrchestrator",
    "OrchestrationResult",
    "OverlayFrame",
    "OverlayRenderer",
]

__version__ = "0.1.0"
