from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WindowInfo:
    name: str
    handle: int | None = None
    process_id: int | None = None
    is_visible: bool = True
    bounds: tuple[int, int, int, int] | None = None
    status: str | None = None
    source: str = "stub"


@dataclass(slots=True)
class TreeNodeInfo:
    name: str
    control_type: str
    bounds: tuple[int, int, int, int] | None = None
    automation_id: str | None = None
    class_name: str | None = None
    role: str | None = None
    process_id: int | None = None
    window_title: str | None = None
    source: str = "stub"


@dataclass(slots=True)
class DesktopSnapshot:
    active_window: WindowInfo | None = None
    windows: list[WindowInfo] = field(default_factory=list)
    screenshot: bytes | None = None
    screenshot_path: str | None = None
    cursor: tuple[int, int] | None = None
    tree_nodes: list[TreeNodeInfo] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PerceptionError(RuntimeError):
    pass


class Perception:
    """Desktop perception facade with real Windows-MCP backend support."""

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    def snapshot(self, with_screenshot: bool = False) -> DesktopSnapshot:
        if self._backend is None:
            return DesktopSnapshot(metadata={"status": "stubbed", "source": "dev-workspace"})

        if hasattr(self._backend, "get_state"):
            state = self._backend.get_state(use_vision=with_screenshot, as_bytes=with_screenshot)
            return self._from_backend_state(state)

        raise PerceptionError("Backend does not expose get_state().")

    def list_windows(self) -> list[WindowInfo]:
        if self._backend is None:
            return []

        if hasattr(self._backend, "get_windows"):
            windows, _ = self._backend.get_windows()
            return [self._from_backend_window(window) for window in windows]

        raise PerceptionError("Backend does not expose get_windows().")

    def get_active_window(self) -> WindowInfo | None:
        if self._backend is None:
            return None

        if hasattr(self._backend, "get_active_window"):
            window = self._backend.get_active_window()
            return self._from_backend_window(window) if window is not None else None

        raise PerceptionError("Backend does not expose get_active_window().")

    @staticmethod
    def _from_backend_window(window: Any) -> WindowInfo:
        bounds = None
        box = getattr(window, "bounding_box", None)
        if box is not None:
            bounds = (box.left, box.top, box.right, box.bottom)
        return WindowInfo(
            name=getattr(window, "name", ""),
            handle=getattr(window, "handle", None),
            process_id=getattr(window, "process_id", None),
            is_visible=getattr(window, "status", None) not in {"MINIMIZED", "HIDDEN"},
            bounds=bounds,
            status=str(getattr(window, "status", None)) if getattr(window, "status", None) else None,
            source="windows-mcp",
        )

    @staticmethod
    def _from_backend_tree_state(tree_state: Any) -> list[TreeNodeInfo]:
        nodes: list[TreeNodeInfo] = []
        for node in getattr(tree_state, "interactive_nodes", []) or []:
            box = getattr(node, "bounding_box", None)
            bounds = (box.left, box.top, box.right, box.bottom) if box is not None else None
            nodes.append(
                TreeNodeInfo(
                    name=getattr(node, "name", ""),
                    control_type=getattr(node, "control_type", ""),
                    bounds=bounds,
                    automation_id=getattr(node, "automation_id", None),
                    class_name=getattr(node, "class_name", None),
                    role=getattr(node, "role", None),
                    process_id=getattr(node, "process_id", None),
                    window_title=getattr(node, "window_title", None),
                    source="windows-mcp",
                )
            )
        return nodes

    @staticmethod
    def _from_backend_state(state: Any) -> DesktopSnapshot:
        windows = []
        seen: set[tuple[int | None, str]] = set()

        def add_window(window: Any) -> None:
            info = Perception._from_backend_window(window)
            key = (info.handle, info.name)
            if key in seen:
                return
            seen.add(key)
            windows.append(info)

        for attr_name in ("windows", "visible_windows", "all_windows", "context_windows"):
            for window in getattr(state, attr_name, []) or []:
                add_window(window)

        active_window = getattr(state, "active_window", None)
        if active_window is not None:
            add_window(active_window)

        tree_state = getattr(state, "tree_state", None)
        cursor = getattr(state, "cursor_position", None)
        screenshot = getattr(state, "screenshot", None)
        if isinstance(screenshot, str):
            screenshot = screenshot.encode("utf-8")
        screenshot_path = getattr(state, "screenshot_path", None)
        metadata = {"source": "windows-mcp"}
        if screenshot_path is not None:
            metadata["screenshot_path"] = screenshot_path
        if screenshot is not None:
            metadata["has_screenshot"] = True
            metadata["screenshot_bytes"] = len(screenshot)
        return DesktopSnapshot(
            active_window=Perception._from_backend_window(active_window)
            if active_window is not None
            else None,
            windows=windows,
            screenshot=screenshot,
            screenshot_path=screenshot_path,
            cursor=cursor,
            tree_nodes=Perception._from_backend_tree_state(tree_state) if tree_state else [],
            metadata=metadata,
        )
