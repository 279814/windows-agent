from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any
import sys


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


def _ensure_namespace_package(module_name: str, package_path: Path) -> ModuleType:
    module = sys.modules.get(module_name)
    if module is None:
        module = ModuleType(module_name)
        module.__path__ = [str(package_path)]
        sys.modules[module_name] = module
    else:
        existing_path = list(getattr(module, "__path__", []))
        if str(package_path) not in existing_path:
            existing_path.append(str(package_path))
            module.__path__ = existing_path
    return module


def load_windows_mcp_desktop(source_root: str | Path) -> WindowsMcpBackend:
    root = Path(source_root)
    src_root = root / "src"
    package_root = src_root / "windows_mcp"
    service_path = package_root / "desktop" / "service.py"
    if not service_path.exists():
        raise BackendLoadError(f"Windows-MCP service module not found: {service_path}")

    _ensure_namespace_package("windows_mcp", package_root)
    _ensure_namespace_package("windows_mcp.desktop", package_root / "desktop")

    spec = spec_from_file_location("windows_mcp.desktop.service", service_path)
    if spec is None or spec.loader is None:
        raise BackendLoadError(f"Unable to load module from: {service_path}")

    module = module_from_spec(spec)
    sys.modules[spec.name] = module
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
                if getattr(state, "display_id", None) is None:
                    for attr in ("monitor_id", "screen_id", "display_index"):
                        value = getattr(state, attr, None)
                        if value is not None:
                            setattr(state, "display_id", value)
                            break
                if getattr(state, "dpi_scale", None) is None:
                    for attr in ("scale_factor", "dpi_scaling", "dpi_scale_factor"):
                        value = getattr(state, attr, None)
                        if value is not None:
                            try:
                                setattr(state, "dpi_scale", float(value))
                            except Exception:
                                setattr(state, "dpi_scale", value)
                            break
                if getattr(state, "monitor_bounds", None) is None:
                    for attr in ("monitors", "displays", "screen_bounds"):
                        value = getattr(state, attr, None)
                        if value:
                            setattr(state, "monitor_bounds", value)
                            break
                if getattr(state, "is_user_control_active", None) is None:
                    control_flags = ["user_control_active", "manual_control_active", "operator_control_active", "user_taking_over"]
                    for attr in control_flags:
                        value = getattr(state, attr, None)
                        if value is not None:
                            setattr(state, "is_user_control_active", lambda value=value: bool(value))
                            break
            except Exception:
                pass
            return state

        desktop.get_state = get_state_with_focus

    original_is_user_control_active = getattr(desktop, "is_user_control_active", None)
    if not callable(original_is_user_control_active):
        def is_user_control_active() -> bool:
            try:
                state = desktop.get_state() if callable(getattr(desktop, "get_state", None)) else None
                if state is None:
                    return False
                for attr in ("is_user_control_active", "user_control_active", "manual_control_active", "operator_control_active", "user_taking_over"):
                    value = getattr(state, attr, None)
                    if callable(value):
                        try:
                            return bool(value())
                        except Exception:
                            continue
                    if value is not None:
                        return bool(value)
            except Exception:
                return False
            return False

        desktop.is_user_control_active = is_user_control_active
    return WindowsMcpBackend(desktop=desktop, source_path=service_path)


def build_backend_bundle(source_root: str | Path) -> BackendBundle:
    backend = load_windows_mcp_desktop(source_root)
    return BackendBundle(
        perception=backend.desktop,
        executor=backend.desktop,
        desktop=backend.desktop,
        source_path=backend.source_path,
    )
