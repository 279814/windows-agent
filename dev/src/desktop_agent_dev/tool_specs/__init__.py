from .desktop_tools import register_desktop_tools
from .input_tools import register_input_tools
from .task_tools import register_task_tools
from .vision_tools import register_vision_tools
from .window_tools import register_window_tools

__all__ = [
    "register_desktop_tools",
    "register_input_tools",
    "register_task_tools",
    "register_vision_tools",
    "register_window_tools",
]
