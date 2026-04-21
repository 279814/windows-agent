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
    desktop = module.Desktop()
    return WindowsMcpBackend(desktop=desktop, source_path=service_path)


def build_backend_bundle(source_root: str | Path) -> BackendBundle:
    backend = load_windows_mcp_desktop(source_root)
    return BackendBundle(
        perception=backend.desktop,
        executor=backend.desktop,
        desktop=backend.desktop,
        source_path=backend.source_path,
    )
