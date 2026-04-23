from __future__ import annotations

from types import SimpleNamespace
import pytest

try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
    from desktop_agent_dev.executor import Executor
    from desktop_agent_dev.mcp_server import create_server
    MCP_IMPORT_ERROR = None
except OSError as exc:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    Executor = None
    create_server = None
    MCP_IMPORT_ERROR = exc


RESOURCE_URIS = [
    "desktop-agent-dev://readme",
    "desktop-agent-dev://catalog",
    "desktop-agent-dev://capabilities",
    "desktop-agent-dev://security",
    "desktop-agent-dev://manifest",
    "desktop-agent-dev://tool-handbook",
    "desktop-agent-dev://tool-index",
]


def test_server_registers_tools() -> None:
    if create_server is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    assert server.mcp is not None
    assert server.services is not None


def test_server_tools_return_structured_payloads() -> None:
    if create_server is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    snapshot = server.services.perception.snapshot()
    assert snapshot.metadata["status"] == "stubbed"
    assert snapshot.metadata["source"] == "dev-workspace"


def test_server_registers_window_tools() -> None:
    if create_server is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    assert server.services.executor.switch_window("main").tool == "window_switch"
    assert server.services.executor.resize_window(name="main", width=100, height=200).tool == "window_resize"


class _LaunchState:
    def __init__(self, active_window: object | None, windows: list[object] | None = None) -> None:
        self.active_window = active_window
        self.windows = windows or ([active_window] if active_window is not None else [])


class _LaunchWindow:
    def __init__(self, name: str) -> None:
        self.name = name
        self.window_title = name


class _LaunchBackend:
    def __init__(self, detected_name: str, pid: int = 4242) -> None:
        self.detected_name = detected_name
        self.pid = pid
        self.calls: list[tuple[str, tuple, dict]] = []
        self._state = _LaunchState(_LaunchWindow("main"), windows=[_LaunchWindow("main")])

    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        launched = _LaunchWindow(self.detected_name)
        windows = list(self._state.windows)
        windows.append(launched)
        self._state = _LaunchState(launched, windows=windows)
        return (f"Launched {name}. [verification=name:{self.detected_name}]", 0, self.pid)

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> _LaunchState:
        return self._state


class _DelayedLaunchBackend(_LaunchBackend):
    def __init__(self, detected_name: str) -> None:
        super().__init__(detected_name=detected_name, pid=0)
        self._reads = 0
        self._before = self._state
        launched = _LaunchWindow(self.detected_name)
        self._after = _LaunchState(launched, windows=list(self._state.windows) + [launched])

    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        return (f"Launch returned pending for {name}. [verification=name:{self.detected_name}]", 1, 0)

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> _LaunchState:
        self._reads += 1
        if self._reads >= 3:
            self._state = self._after
            return self._after
        return self._before


class _ProcessVerifiedLaunchBackend(_LaunchBackend):
    def __init__(self, detected_name: str = "main") -> None:
        super().__init__(detected_name=detected_name, pid=27236)

    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        return (f"Launched via start menu shortcut: steam (score=90). 27236\r\n [attempted=direct:{name}; verification=process:steam.exe]", 0, 27236)


class _TypeValidationBackend:
    def __init__(self) -> None:
        self._state = SimpleNamespace(
            focused_control={"name": "七", "value": "", "text": "", "control_type": "按钮", "window_title": "计算器"}
        )

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> SimpleNamespace:
        return self._state

    def type(
        self,
        loc: tuple[int, int],
        text: str,
        press_enter: bool = False,
        clear: bool = False,
        caret_position: str = "idle",
    ) -> None:
        return None


def test_input_launch_app_tool_aligns_top_level_ok_on_success() -> None:
    if create_server is None or Executor is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    server.services.executor = Executor(backend=_LaunchBackend("File Explorer"))

    result = server.tool_registry.specs["input_launch_app"].executor(name="explorer")

    assert result["ok"] is True
    assert result["data"]["ok"] is True
    assert result["data"]["payload"]["verification_status"] == "success"


def test_input_launch_app_tool_aligns_top_level_ok_on_target_mismatch() -> None:
    if create_server is None or Executor is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    server.services.executor = Executor(backend=_LaunchBackend("C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe"))

    result = server.tool_registry.specs["input_launch_app"].executor(name="calc")

    assert result["ok"] is False
    assert result["data"]["ok"] is False
    assert result["message"] == "target mismatch:calc->C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe"
    assert result["data"]["payload"]["verification_status"] == "target_mismatch"
    assert result["data"]["payload"]["result_code"] == "TARGET_MISMATCH"


def test_input_launch_app_tool_recovers_top_level_ok_when_backend_pid_missing_but_window_verified() -> None:
    if create_server is None or Executor is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    server.services.executor = Executor(backend=_DelayedLaunchBackend("微信"))

    result = server.tool_registry.specs["input_launch_app"].executor(name="微信")

    assert result["ok"] is True
    assert result["data"]["ok"] is True
    assert result["data"]["payload"]["verification_status"] == "success"
    assert result["data"]["payload"]["result_code"] == "OK"
    assert result["data"]["payload"]["detected_window_name"] == "微信"


def test_input_launch_app_tool_accepts_backend_process_verification() -> None:
    if create_server is None or Executor is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    server.services.executor = Executor(backend=_ProcessVerifiedLaunchBackend())

    result = server.tool_registry.specs["input_launch_app"].executor(name="steam.exe - 快捷方式")

    assert result["ok"] is True
    assert result["data"]["ok"] is True
    assert result["data"]["payload"]["verification_source"] == "process"
    assert result["data"]["payload"]["verification_hint"] == "steam.exe"
    assert result["data"]["payload"]["verification_status"] == "success"


def test_input_type_tool_propagates_failed_validation_to_top_level() -> None:
    if create_server is None or Executor is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()
    server.services.executor = Executor(backend=_TypeValidationBackend())
    server.services.perception = SimpleNamespace(
        snapshot=lambda with_screenshot=False: SimpleNamespace(
            focused_control={"name": "七", "value": "", "text": "", "control_type": "按钮", "window_title": "计算器"}
        )
    )

    result = server.tool_registry.specs["input_type"].executor(text="23")

    assert result["ok"] is False
    assert result["message"] == "validation_failed:23"
    assert result["data"]["ok"] is False
    assert result["data"]["payload"]["validation"]["passed"] is False


def test_placeholder_vision_tools_report_not_implemented() -> None:
    if create_server is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    server = create_server()

    for tool_name in ("vision_capture", "ocr_extract", "vision_locate", "ui_match"):
        result = server.tool_registry.specs[tool_name].executor()
        assert result["ok"] is False
        assert result["error"]["code"] == "not_implemented"
        assert result["data"]["implemented"] is False


async def _mcp_smoke_chain() -> dict[str, object]:
    if create_server is None or ClientSession is None or StdioServerParameters is None or stdio_client is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    import asyncio

    params = StdioServerParameters(
        command="python",
        args=["-m", "desktop_agent_dev"],
        cwd="E:/developdata/code/windows-mcp/dev",
        env={"PYTHONPATH": "E:/developdata/code/windows-mcp/dev/src"},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init = await session.initialize()
            resources = await session.list_resources()
            resource_uris = [str(item.uri) for item in resources.resources]
            read_results = {}
            for uri in RESOURCE_URIS:
                result = await session.read_resource(uri)
                read_results[uri] = result
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            snapshot = await session.call_tool("desktop_snapshot", {"with_screenshot": False})
            move = await session.call_tool("input_move", {"x": 10, "y": 20})
            window_switch = await session.call_tool("window_switch", {"name": "main"})
            window_focus = await session.call_tool("window_focus", {"name": "main"})
            window_resize = await session.call_tool("window_resize", {"name": "main", "width": 640, "height": 480})
            task_plan = await session.call_tool("task_plan", {"goal": "打开记事本并输入 hello"})
            task_state = await session.call_tool("task_state", {"task_id": "demo"})
            vision_capture = await session.call_tool("vision_capture", {})
            ocr_extract = await session.call_tool("ocr_extract", {})
            ui_match = await session.call_tool("ui_match", {})
            return {
                "initialize": init,
                "resource_uris": resource_uris,
                "read_results": read_results,
                "tool_names": tool_names,
                "snapshot": snapshot,
                "move": move,
                "window_switch": window_switch,
                "window_focus": window_focus,
                "window_resize": window_resize,
                "task_plan": task_plan,
                "task_state": task_state,
                "vision_capture": vision_capture,
                "ocr_extract": ocr_extract,
                "ui_match": ui_match,
            }


def test_mcp_smoke_chain() -> None:
    if create_server is None or ClientSession is None or StdioServerParameters is None or stdio_client is None:
        pytest.skip(f"mcp runtime unavailable in this environment: {MCP_IMPORT_ERROR}")
    import asyncio

    result = asyncio.run(_mcp_smoke_chain())
    assert "desktop-agent-dev://readme" in result["resource_uris"]
    assert "desktop-agent-dev://tool-index" in result["resource_uris"]
    assert "desktop_snapshot" in result["tool_names"]
    assert "input_move" in result["tool_names"]
    assert "window_switch" in result["tool_names"]
    assert "window_focus" in result["tool_names"]
    assert "window_resize" in result["tool_names"]
    assert "task_plan" in result["tool_names"]
    assert "task_state" in result["tool_names"]
    assert "vision_capture" in result["tool_names"]
    assert "ocr_extract" in result["tool_names"]
    assert "ui_match" in result["tool_names"]
    assert result["snapshot"].content
    assert result["move"].content
    assert result["window_switch"].content
    assert result["window_focus"].content
    assert result["window_resize"].content
    assert result["task_plan"].content
    assert result["task_state"].content
    assert result["vision_capture"].content
    assert result["ocr_extract"].content
    assert result["ui_match"].content
