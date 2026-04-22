from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


class BackendLoadError(RuntimeError):
    pass


@dataclass(slots=True)
class WindowsMcpBackend:
    desktop: Any
    source_path: Path


@dataclass(slots=True)
class BackendBundle:
    perception: Any
    executor: Any
    desktop: Any
    source_path: Path


def load_windows_mcp_desktop(source_root: str | Path) -> WindowsMcpBackend:
    root = Path(source_root)
    service_path = root / "src" / "windows_mcp" / "desktop" / "service.py"
    if not service_path.exists():
        raise BackendLoadError(f"Windows-MCP service module not found: {service_path}")

    spec = spec_from_file_location("windows_mcp.desktop.service", service_path)
    if spec is None or spec.loader is None:
        raise BackendLoadError(f"Unable to load module from: {service_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    desktop_state_cls = getattr(module, "DesktopState", None)
    if desktop_state_cls is not None:
        init_code = getattr(getattr(desktop_state_cls, "__init__", None), "__code__", None)
        if init_code is not None and "focused_control" not in init_code.co_varnames:
            class DesktopStateCompat:
                def __init__(self, *args: Any, **kwargs: Any) -> None:
                    field_order = [
                        "active_desktop",
                        "all_desktops",
                        "active_window",
                        "windows",
                        "screenshot",
                        "cursor_position",
                        "screenshot_original_size",
                        "screenshot_region",
                        "screenshot_displays",
                        "screenshot_backend",
                        "tree_state",
                        "focused_control",
                    ]
                    for index, value in enumerate(args):
                        if index < len(field_order):
                            kwargs.setdefault(field_order[index], value)
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            module.DesktopState = DesktopStateCompat

    desktop = module.Desktop()
    original_get_state = getattr(desktop, "get_state", None)
    if callable(original_get_state):
        def get_state_with_focus(*args: Any, **kwargs: Any):
            state = original_get_state(*args, **kwargs)
            try:
                focused_control = getattr(state, "focused_control", None)
                if focused_control is None and hasattr(state, "tree_state") and getattr(state, "tree_state", None) is not None:
                    focused_control = getattr(state.tree_state, "focused_node", None) or getattr(state.tree_state, "focus_node", None) or getattr(state.tree_state, "focused_control", None)
                    if focused_control is not None:
                        setattr(state, "focused_control", focused_control)
            except Exception:
                pass
            return state

        desktop.get_state = get_state_with_focus
    return WindowsMcpBackend(desktop=desktop, source_path=service_path)


def build_backend_bundle(source_root: str | Path) -> BackendBundle:
    backend = load_windows_mcp_desktop(source_root)
    return BackendBundle(
        perception=backend.desktop,
        executor=backend.desktop,
        desktop=backend.desktop,
        source_path=backend.source_path,
    )
