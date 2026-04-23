from desktop_agent_dev.executor import Executor, InputResult


class FakeWindowState:
    def __init__(
        self,
        name: str = "main",
        handle: int | None = 1,
        status: str = "normal",
        pid: int | None = None,
        bounds: list[int] | None = None,
        is_visible: bool | None = True,
    ) -> None:
        self.name = name
        self.handle = handle
        self.status = status
        self.pid = pid if pid is not None else handle
        self.window_title = name
        self.bounds = bounds or [0, 0, 800, 600]
        self.is_visible = is_visible
        self.value = ""


class FakeDesktopState:
    def __init__(self, active_window: FakeWindowState | None, windows: list[FakeWindowState] | None = None) -> None:
        self.active_window = active_window
        self.windows = windows or ([active_window] if active_window is not None else [])
        self.focused_control = active_window


class FakeExecBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._state = FakeDesktopState(FakeWindowState(), windows=[FakeWindowState()])

    def click(self, loc: tuple[int, int], button: str = "left", clicks: int = 1) -> None:
        self.calls.append(("click", (loc,), {"button": button, "clicks": clicks}))

    def move(self, loc: tuple[int, int]) -> None:
        self.calls.append(("move", (loc,), {}))

    def drag(self, loc: tuple[int, int]) -> None:
        self.calls.append(("drag", (loc,), {}))

    def type(
        self,
        loc: tuple[int, int],
        text: str,
        press_enter: bool = False,
        clear: bool = False,
        caret_position: str = "idle",
    ) -> None:
        self.calls.append(
            (
                "type",
                (loc,),
                {"text": text, "press_enter": press_enter, "clear": clear, "caret_position": caret_position},
            )
        )
        active = getattr(self._state, "active_window", None)
        if active is not None:
            setattr(active, "value", text)

    def shortcut(self, keys: str) -> None:
        self.calls.append(("shortcut", (keys,), {}))

    def scroll(self, direction: str, wheel_times: int = 1) -> None:
        self.calls.append(("scroll", (), {"direction": direction, "wheel_times": wheel_times}))

    def multi_select(self, press_ctrl: bool, locs: list[tuple[int, int]]) -> None:
        self.calls.append(("multi_select", (), {"press_ctrl": press_ctrl, "locs": locs}))

    def multi_edit(self, edits: list[tuple[int, int, str]]) -> None:
        self.calls.append(("multi_edit", (), {"edits": edits}))

    def switch_app(self, name: str) -> str:
        self.calls.append(("switch_app", (name,), {}))
        return f"switch:{name}"

    def focus_app(self, name: str) -> str:
        self.calls.append(("focus_app", (name,), {}))
        return f"focus:{name}"

    def close_app(self, name: str) -> str:
        self.calls.append(("close_app", (name,), {}))
        self._state = FakeDesktopState(None)
        return f"close:{name}"

    def resize_app(self, name=None, size=None, loc=None) -> str:
        self.calls.append(("resize_app", (), {"name": name, "size": size, "loc": loc}))
        return f"resize:{name}"

    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        display_names = {
            "calc.exe": "Calculator",
            "explorer.exe": "File Explorer",
            "notepad.exe": "desktop-agent-dev input_type smoke - Notepad",
            "mspaint.exe": "Paint",
        }
        target_name = display_names.get(name, name)
        new_window = FakeWindowState(name=target_name, handle=99, status="normal")
        current_windows = list(self._state.windows)
        current_windows.append(new_window)
        self._state = FakeDesktopState(new_window, windows=current_windows)
        return (f"Launched {name}. [verification=name:{target_name}]", 0, 4242)

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> FakeDesktopState:
        return self._state


def test_executor_stubs_return_values() -> None:
    executor = Executor()
    assert executor.click(10, 20).detail == "clicked:10,20:left:1"
    assert executor.type_text("abc").detail == "typed:abc"


def test_executor_uses_backend_for_input() -> None:
    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.click(100, 200, button="right", clicks=2)
    assert result == InputResult(action="input_click", ok=True, detail="clicked:100,200:right:2", payload=result.payload, tool="input_click")
    assert executor.move(9, 8).detail == "moved:9,8"
    assert executor.type_text("hello", press_enter=True, clear=True, caret_position="end").detail == "typed:hello:enter"
    assert executor.shortcut("ctrl+s").detail == "shortcut:ctrl+s"
    assert executor.scroll("down", amount=3).detail == "scrolled:down:3"
    assert executor.multi_select([(1, 2), (3, 4)], press_ctrl=True).detail == "multi_selected:2:ctrl"
    assert executor.multi_edit([(1, 2, "a"), (3, 4, "b")]).detail == "multi_edited:2"
    assert executor.switch_window("main").detail == "switch:main"
    assert executor.focus_window("main").detail == "focus:main"
    assert executor.resize_window(name="main", width=100, height=200).detail == "resize:main"
    close_result = executor.close_window("main")
    assert close_result.ok is True
    assert close_result.payload is not None
    assert close_result.payload["post_close_verified"] is True
    launch_result = executor.launch_app("calc")
    assert launch_result.action == "input_launch_app"
    assert launch_result.ok is True
    assert launch_result.detail == "launched:calc"

    call_names = [name for name, _, _ in backend.calls]
    assert call_names == [
        "click",
        "move",
        "type",
        "shortcut",
        "scroll",
        "multi_select",
        "multi_edit",
        "switch_app",
        "focus_app",
        "resize_app",
        "close_app",
        "launch_app",
    ]
    assert result.payload is not None
    assert "element" in result.payload
    assert "found" in result.payload["element"]
    move_result = executor.move(9, 8)
    assert move_result.payload is not None
    assert move_result.payload["x"] == 9
    assert "element" in move_result.payload
    drag_result = executor.drag((1, 2), (3, 4))
    assert drag_result.payload is not None
    assert drag_result.payload["start"]["x"] == 1
    assert drag_result.payload["end"]["y"] == 4
    shortcut_result = executor.shortcut("ctrl+s")
    assert shortcut_result.payload is not None
    assert shortcut_result.payload["injection_result"]["method"] == "backend.shortcut"
    scroll_result = executor.scroll("down", amount=3)
    assert scroll_result.payload is not None
    assert scroll_result.payload["direction"] == "down"
    assert scroll_result.payload["amount"] == 3
    multi_select_result = executor.multi_select([(1, 2), (3, 4)], press_ctrl=True)
    assert multi_select_result.payload is not None
    assert len(multi_select_result.payload["targets"]) == 2
    multi_edit_result = executor.multi_edit([(1, 2, "a"), (3, 4, "b")])
    assert multi_edit_result.payload is not None
    assert len(multi_edit_result.payload["items"]) == 2


class FakeHitBox:
    def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class FakeHitNode:
    def __init__(self, name: str, control_type: str, box: FakeHitBox, automation_id: str | None = None, class_name: str | None = None, role: str | None = None, leaf: bool = True, interactive: bool = True) -> None:
        self.name = name
        self.control_type = control_type
        self.bounding_box = box
        self.automation_id = automation_id
        self.class_name = class_name
        self.role = role
        self.is_leaf = leaf
        self.is_interactive = interactive
        self.is_transparent = False
        self.is_decorative = False
        self.children = []


class FakeHitTreeState:
    def __init__(self) -> None:
        self.interactive_nodes = [
            FakeHitNode("Container", "Pane", FakeHitBox(0, 0, 200, 200), class_name="Pane", leaf=False, interactive=False),
            FakeHitNode("PrimaryButton", "Button", FakeHitBox(20, 20, 120, 120), automation_id="primary", role="push button"),
            FakeHitNode("Overlay", "Text", FakeHitBox(10, 10, 140, 140), class_name="TextBlock", leaf=True, interactive=False),
        ]


class FakeHitState:
    def __init__(self) -> None:
        self.tree_state = FakeHitTreeState()


class FakeHitBackend:
    def click(self, loc: tuple[int, int], button: str = "left", clicks: int = 1) -> None:
        self.last_click = (loc, button, clicks)

    def get_tree_state(self) -> FakeHitTreeState:
        return FakeHitTreeState()

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> FakeHitState:
        return FakeHitState()


class FakeTextEditorBackend(FakeExecBackend):
    class _EditorTreeState:
        def __init__(self) -> None:
            self.interactive_nodes = [
                FakeHitNode(
                    "",
                    "Edit",
                    FakeHitBox(800, 500, 1400, 900),
                    class_name="RichEditD2DPT",
                    role="document",
                    leaf=False,
                    interactive=True,
                )
            ]

    class _EditorState(FakeDesktopState):
        def __init__(self) -> None:
            window = FakeWindowState(name="test.txt - Notepad", handle=77, status="normal", bounds=[700, 450, 1500, 980])
            super().__init__(window, windows=[window])
            self.focused_control = {
                "name": None,
                "control_type": "Edit",
                "class_name": "RichEditD2DPT",
                "role": "document",
                "window_title": "test.txt - Notepad",
                "bounds": [800, 500, 1400, 900],
            }
            self.tree_state = FakeTextEditorBackend._EditorTreeState()

    def get_tree_state(self) -> _EditorTreeState:
        return FakeTextEditorBackend._EditorTreeState()

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> _EditorState:
        return FakeTextEditorBackend._EditorState()


def test_hit_test_prefers_more_specific_overlap_candidate() -> None:
    backend = FakeHitBackend()
    executor = Executor(backend=backend)
    result = executor.click(30, 30)

    assert result.payload is not None
    assert result.payload["element"]["name"] == "PrimaryButton"
    assert result.payload["element"]["found"] is True
    assert result.payload["element"]["confidence"] > 0.5
    assert result.payload["element"]["z_index"] == 1


def test_hit_test_recovers_text_editor_region_without_unknown() -> None:
    backend = FakeTextEditorBackend()
    executor = Executor(backend=backend)

    result = executor.click(1000, 600)

    assert result.payload is not None
    assert result.payload["element"]["found"] is True
    assert result.payload["element"]["type"] == "Edit"
    assert result.payload["element"]["semantic_role"] in {"document", "text_input"}
    assert result.payload["element"]["source"] in {"tree_state", "snapshot", "focused_control"}


def test_executor_close_window_uses_backend_close_app_and_verifies_state_change() -> None:
    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.close_window("main")

    assert result.ok is True
    assert result.tool == "window_close"
    assert result.payload is not None
    assert result.payload["close_strategy"] == "backend.close_app"
    assert result.payload["outcome"] in {"execution_succeeded", "success_wm_close_degraded"}
    assert result.payload["post_close_verified"] is True
    assert result.payload["backend_response"] == ("Closed main.", 0)
    assert result.payload["exit_code"] == 0
    assert result.detail
    assert backend.calls[-1][0] == "close_app"
    assert backend.calls[-1][1] == ("main",)


class FakeFailBackend(FakeExecBackend):
    def close_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("close_app", (name,), {}))
        return (f"Failed to close {name}.", 1)


class FakeLaunchMismatchBackend(FakeExecBackend):
    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        wrong_window = FakeWindowState(name="Codex", handle=100, status="normal")
        self._state = FakeDesktopState(wrong_window, windows=list(self._state.windows))
        return (f"Launched via start menu shortcut: endnote (score=61). [verification=name:{wrong_window.name}]", 0, 0)


class FakeMpicalcBackend(FakeExecBackend):
    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        wrong_window = FakeWindowState(name="C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe", handle=101, status="normal")
        current_windows = list(self._state.windows)
        current_windows.append(wrong_window)
        self._state = FakeDesktopState(wrong_window, windows=current_windows)
        return (f"Launched {name} without PID confirmation, but window appeared. [verification=name:{wrong_window.name}]", 0, 17000)


class FakeDelayedVerifiedLaunchBackend(FakeExecBackend):
    def __init__(self, requested_name: str, detected_name: str, status: int = 1, pid: int = 0) -> None:
        super().__init__()
        self.requested_name = requested_name
        self.detected_name = detected_name
        self.status = status
        self.pid = pid
        self.state_reads = 0
        self._before = self._state
        self._after = FakeDesktopState(
            FakeWindowState(name=detected_name, handle=102, status="normal"),
            windows=list(self._state.windows) + [FakeWindowState(name=detected_name, handle=102, status="normal")],
        )

    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        return (f"Launch returned pending for {name}. [verification=name:{self.detected_name}]", self.status, self.pid)

    def get_state(self, use_vision: bool = False, as_bytes: bool = False) -> FakeDesktopState:
        self.state_reads += 1
        if self.state_reads >= 3:
            self._state = self._after
            return self._after
        return self._before


class FakeProcessVerifiedLaunchBackend(FakeExecBackend):
    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        return (f"Launched via start menu shortcut: steam (score=90). 27236\r\n [attempted=direct:{name}; verification=process:steam.exe]", 0, 27236)


class FakeLocalizedCalcBackend(FakeExecBackend):
    def launch_app(self, name: str) -> tuple[str, int, int]:
        self.calls.append(("launch_app", (name,), {}))
        localized_window = FakeWindowState(name="计算器", handle=103, status="normal")
        current_windows = list(self._state.windows)
        current_windows.append(localized_window)
        self._state = FakeDesktopState(localized_window, windows=current_windows)
        return (f"Launched {name}. [verification=name:{localized_window.name}]", 0, 4243)


class FakeWindowLifecycleBackend(FakeExecBackend):
    def __init__(self, maximize_status: str = "normal", minimize_status: str = "normal", restore_status: str = "maximized") -> None:
        super().__init__()
        self.maximize_status = maximize_status
        self.minimize_status = minimize_status
        self.restore_status = restore_status

    def maximize_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("maximize_app", (name,), {}))
        self._state.active_window.status = self.maximize_status
        for window in self._state.windows:
            if name is None or window.name == name:
                window.status = self.maximize_status
        return (f"Maximized {name} window.", 0)

    def minimize_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("minimize_app", (name,), {}))
        self._state.active_window.status = self.minimize_status
        for window in self._state.windows:
            if name is None or window.name == name:
                window.status = self.minimize_status
        return (f"Minimized {name} window.", 0)

    def restore_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("restore_app", (name,), {}))
        self._state.active_window.status = self.restore_status
        for window in self._state.windows:
            if name is None or window.name == name:
                window.status = self.restore_status
        return (f"Restored {name} window.", 0)


class FakeSwitchFailureBackend(FakeExecBackend):
    def switch_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("switch_app", (name,), {}))
        return (f"Application {name} not found.", 1)


class FakeDuplicateTitleMinimizeBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        primary = FakeWindowState(name="计算器", handle=101, status="normal")
        secondary = FakeWindowState(name="计算器", handle=202, status="maximized")
        self._state = FakeDesktopState(primary, windows=[primary, secondary])

    def minimize_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("minimize_app", (name,), {}))
        secondary = next(window for window in self._state.windows if window.handle == 202)
        self._state = FakeDesktopState(secondary, windows=[secondary])
        return (f"{name} minimized.", 0)


class FakeNormalizedSwitchBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        self._state = FakeDesktopState(
            FakeWindowState(name="Codex", handle=11, status="maximized", pid=11),
            windows=[
                FakeWindowState(name="Codex", handle=11, status="maximized", pid=11),
                FakeWindowState(name="test.txt - Notepad", handle=22, status="normal", pid=220),
            ],
        )

    def switch_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("switch_app", (name,), {}))
        target = FakeWindowState(name="*test.txt - Notepad", handle=22, status="normal", pid=220)
        self._state = FakeDesktopState(
            target,
            windows=[target, FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)],
        )
        return ("Switched to *Test.Txt - Notepad window.", 0)


class FakeRestoredFromMinimizedBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        self._state = FakeDesktopState(
            FakeWindowState(name="Codex", handle=11, status="maximized", pid=11),
            windows=[
                FakeWindowState(name="Codex", handle=11, status="maximized", pid=11),
                FakeWindowState(name="test.txt - Notepad", handle=22, status="minimized", pid=220, is_visible=False),
            ],
        )

    def switch_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("switch_app", (name,), {}))
        target = FakeWindowState(name="test.txt - Notepad", handle=22, status="normal", pid=220, is_visible=True)
        self._state = FakeDesktopState(
            target,
            windows=[target, FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)],
        )
        return ("Restored Test.Txt - Notepad from minimized and switched to it.", 0)


class FakeGeometryMaximizeBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        target = FakeWindowState(name="计算器", handle=303, status="normal", pid=3303, bounds=[100, 100, 500, 600])
        self._state = FakeDesktopState(target, windows=[target])

    def maximize_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("maximize_app", (name,), {}))
        target = FakeWindowState(name="计算器", handle=303, status="normal", pid=3303, bounds=[0, 0, 1200, 900])
        self._state = FakeDesktopState(target, windows=[target])
        return ("Maximized 计算器 window.", 0)


class FakeVisibleFlagMinimizeBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        target = FakeWindowState(name="计算器", handle=404, status="normal", pid=4404, is_visible=True)
        other = FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)
        self._state = FakeDesktopState(target, windows=[target, other])

    def minimize_app(self, name: str | None = None) -> tuple[str, int]:
        self.calls.append(("minimize_app", (name,), {}))
        target = FakeWindowState(name="计算器", handle=404, status="normal", pid=4404, is_visible=False)
        other = FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)
        self._state = FakeDesktopState(other, windows=[other, target])
        return ("计算器 minimized.", 0)


class FakeDuplicateTitleCloseBackend(FakeExecBackend):
    def __init__(self) -> None:
        super().__init__()
        primary = FakeWindowState(name="计算器", handle=101, status="normal", pid=1001)
        secondary = FakeWindowState(name="计算器", handle=202, status="normal", pid=2002)
        active = FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)
        self._state = FakeDesktopState(active, windows=[active, primary, secondary])

    def close_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("close_app", (name,), {}))
        active = FakeWindowState(name="Codex", handle=11, status="maximized", pid=11)
        remaining = FakeWindowState(name="计算器", handle=202, status="normal", pid=2002)
        self._state = FakeDesktopState(active, windows=[active, remaining])
        return ("Failed to post WM_CLOSE to 计算器.", 1)


def test_executor_close_window_marks_backend_failure_as_not_ok() -> None:
    backend = FakeFailBackend()
    executor = Executor(backend=backend)

    result = executor.close_window("main")

    assert result.ok is False
    assert result.detail == "Failed to close main."
    assert result.payload is not None
    assert result.payload["close_strategy"] == "backend.close_app"
    assert result.payload["outcome"] == "execution_failed"
    assert result.payload["post_close_verified"] is False
    assert result.payload["exit_code"] == 1


def test_executor_launch_app_returns_complete_result() -> None:
    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("calc")

    assert result.action == "input_launch_app"
    assert result.ok is True
    assert result.detail == "launched:calc"
    assert result.payload is not None
    assert result.tool == "input_launch_app"
    assert result.payload["name"] == "calc"
    assert result.payload["requested_target"] == "calc"
    assert result.payload["matched_target"] == "calc.exe"
    assert "backend_response" in result.payload
    assert "window_detected" in result.payload
    assert result.payload["verification_status"] == "success"
    assert result.payload["result_code"] == "OK"
    assert result.payload["verification_hint"] == "Calculator"
    assert result.payload["matching_instance_count_before"] == 0
    assert result.payload["matching_instance_count_after"] == 1
    assert result.payload["new_instance_detected"] is True
    assert result.payload["new_instance_handles"] == [99]


def test_executor_launch_app_maps_explorer_alias_and_reports_verification() -> None:
    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("explorer")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["requested_target"] == "explorer"
    assert result.payload["matched_target"] == "explorer.exe"
    assert result.payload["resolved_alias"] == "explorer.exe"
    assert result.payload["verification_status"] == "success"
    assert result.payload["result_code"] == "OK"
    assert result.payload["warning"] is None
    assert backend.calls[-1][0] == "launch_app"
    assert backend.calls[-1][1] == ("explorer.exe",)


def test_executor_launch_app_accepts_localized_window_name_for_calc() -> None:
    backend = FakeLocalizedCalcBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("calc")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["matched_target"] == "calc.exe"
    assert result.payload["detected_window_name"] == "计算器"
    assert result.payload["target_matches"] is True
    assert result.payload["verification_status"] == "success"


def test_executor_launch_app_maps_notepad_and_mspaint_aliases() -> None:
    cases = [
        ("notepad", "notepad.exe", "desktop-agent-dev input_type smoke - Notepad"),
        ("mspaint", "mspaint.exe", "Paint"),
    ]

    for requested_name, expected_target, expected_window in cases:
        backend = FakeExecBackend()
        executor = Executor(backend=backend)

        result = executor.launch_app(requested_name)

        assert result.ok is True
        assert result.payload is not None
        assert result.payload["requested_target"] == requested_name
        assert result.payload["matched_target"] == expected_target
        assert result.payload["verification_status"] == "success"
        assert result.payload["result_code"] == "OK"
        assert result.payload["detected_window_name"] == expected_window
        assert backend.calls[-1][1] == (expected_target,)


def test_executor_launch_app_reports_target_mismatch() -> None:
    backend = FakeLaunchMismatchBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("notepad")

    assert result.ok is False
    assert result.payload is not None
    assert result.payload["requested_target"] == "notepad"
    assert result.payload["matched_target"] == "notepad.exe"
    assert result.payload["verification_status"] == "target_mismatch"
    assert result.payload["result_code"] == "TARGET_MISMATCH"
    assert result.payload["warning"] is not None
    assert result.payload["detected_window_name"] == "Codex"
    assert backend.calls[-1][1] == ("notepad.exe",)


def test_executor_launch_app_rejects_mpicalc_for_calc() -> None:
    backend = FakeMpicalcBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("calc")

    assert result.ok is False
    assert result.detail == "target mismatch:calc->C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe"
    assert result.payload is not None
    assert result.payload["requested_target"] == "calc"
    assert result.payload["matched_target"] == "calc.exe"
    assert result.payload["detected_window_name"] == "C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe"
    assert result.payload["verification_hint"] == "C:\\Program Files\\Git\\usr\\bin\\mpicalc.exe"
    assert result.payload["target_matches"] is False
    assert result.payload["verification_status"] == "target_mismatch"
    assert result.payload["result_code"] == "TARGET_MISMATCH"
    assert backend.calls[-1][1] == ("calc.exe",)


def test_executor_window_lifecycle_marks_unverified_state_as_failure() -> None:
    backend = FakeWindowLifecycleBackend(maximize_status="normal", minimize_status="normal", restore_status="maximized")
    executor = Executor(backend=backend)

    maximize = executor.maximize_window("main")
    minimize = executor.minimize_window("main")
    restore = executor.restore_window("main")

    assert maximize.ok is False
    assert maximize.detail == "Maximize verification failed for main."
    assert maximize.payload["verified"] is False

    assert minimize.ok is False
    assert minimize.detail == "Minimize verification failed for main."
    assert minimize.payload["verified"] is False

    assert restore.ok is False
    assert restore.detail == "Restore verification failed for main."
    assert restore.payload["verified"] is False


def test_executor_switch_window_marks_backend_not_found_as_failure() -> None:
    backend = FakeSwitchFailureBackend()
    executor = Executor(backend=backend)

    result = executor.switch_window("main")

    assert result.ok is False
    assert result.detail == "Application main not found."
    assert result.payload["backend_response_code"] == 1
    assert result.payload["verified"] is False


def test_executor_switch_window_normalizes_unsaved_marker_in_title() -> None:
    backend = FakeNormalizedSwitchBackend()
    executor = Executor(backend=backend)

    result = executor.switch_window("test.txt - Notepad")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["verified"] is True
    assert result.payload["current_window"] == "*test.txt - Notepad"
    assert result.payload["matched_by"] == "handle"


def test_executor_focus_window_reports_restored_from_target_state() -> None:
    backend = FakeRestoredFromMinimizedBackend()
    executor = Executor(backend=backend)

    result = executor.focus_window("test.txt - Notepad")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["restored_from_minimized"] is True
    assert result.payload["strategy"] in {"switch_window", "focus_app"}


def test_executor_minimize_accepts_hidden_target_handle_as_success() -> None:
    backend = FakeDuplicateTitleMinimizeBackend()
    executor = Executor(backend=backend)

    result = executor.minimize_window("计算器")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["verified"] is True
    assert result.payload["verification_mode"] == "handle_hidden_after_minimize"
    assert result.payload["target_handle_present_after"] is False
    assert result.payload["active_window_after"]["handle"] == 202


def test_executor_minimize_can_target_specific_handle_for_duplicate_titles() -> None:
    backend = FakeDuplicateTitleMinimizeBackend()
    executor = Executor(backend=backend)

    result = executor.minimize_window("计算器", handle=101)

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["before_handle"] == 101
    assert result.payload["verification_mode"] == "handle_hidden_after_minimize"


def test_executor_minimize_accepts_invisible_target_as_success() -> None:
    backend = FakeVisibleFlagMinimizeBackend()
    executor = Executor(backend=backend)

    result = executor.minimize_window("计算器")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["verification_mode"] == "visibility_hidden_after_minimize"
    assert result.payload["active_window_after"]["name"] == "Codex"


def test_executor_maximize_accepts_bounds_expansion_when_status_lags() -> None:
    backend = FakeGeometryMaximizeBackend()
    executor = Executor(backend=backend)

    result = executor.maximize_window("计算器")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["verified"] is True
    assert result.payload["verification_mode"] in {"bounds_expanded", "backend_ack_active_target"}


def test_executor_close_window_accepts_matching_count_drop_for_duplicate_titles() -> None:
    backend = FakeDuplicateTitleCloseBackend()
    executor = Executor(backend=backend)

    result = executor.close_window("计算器")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["post_close_verified"] is True
    assert result.payload["verification_mode"] == "name_count_decreased"
    assert result.payload["outcome"] == "success_wm_close_degraded"


def test_executor_launch_app_prefers_desktop_shortcut_for_third_party_app(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    desktop_dir = home_dir / "Desktop"
    desktop_dir.mkdir(parents=True)
    shortcut_path = desktop_dir / "Acme Painter.lnk"
    shortcut_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setenv("PUBLIC", str(tmp_path / "public"))

    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("Acme Painter")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["matched_target"] == "Acme Painter"
    assert result.payload["effective_target"] == str(shortcut_path)
    assert result.payload["discovery"]["source"] == "desktop_shortcut"
    assert result.payload["discovery"]["display_name"] == "Acme Painter"
    assert backend.calls[-1][1] == (str(shortcut_path),)


def test_executor_launch_app_prefers_desktop_executable_for_third_party_app(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    desktop_dir = home_dir / "Desktop"
    desktop_dir.mkdir(parents=True)
    exe_path = desktop_dir / "Orbit Studio.exe"
    exe_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setenv("PUBLIC", str(tmp_path / "public"))

    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("Orbit Studio")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["matched_target"] == "Orbit Studio"
    assert result.payload["effective_target"] == str(exe_path)
    assert result.payload["discovery"]["source"] == "desktop_executable"
    assert backend.calls[-1][1] == (str(exe_path),)


def test_executor_launch_app_recovers_when_backend_has_no_pid_but_window_appears() -> None:
    backend = FakeDelayedVerifiedLaunchBackend(requested_name="微信", detected_name="微信", status=1, pid=0)
    executor = Executor(backend=backend)

    result = executor.launch_app("微信")

    assert result.ok is True
    assert result.detail == "launched:微信"
    assert result.payload is not None
    assert result.payload["status"] == 1
    assert result.payload["pid"] == 0
    assert result.payload["window_detected"] is True
    assert result.payload["detected_window_name"] == "微信"
    assert result.payload["target_matches"] is True
    assert result.payload["verification_status"] == "success"
    assert result.payload["result_code"] == "OK"
    assert len(result.payload["verification_attempts"]) >= 2


def test_executor_launch_app_strips_shortcut_noise_for_desktop_shortcut(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    desktop_dir = home_dir / "Desktop"
    desktop_dir.mkdir(parents=True)
    shortcut_path = desktop_dir / "Steam.lnk"
    shortcut_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setenv("PUBLIC", str(tmp_path / "public"))

    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("steam.exe - 快捷方式")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["matched_target"] == "steam"
    assert result.payload["effective_target"] == str(shortcut_path)
    assert result.payload["discovery"]["display_name"] == "Steam"
    assert backend.calls[-1][1] == (str(shortcut_path),)


def test_executor_launch_app_matches_versioned_name_via_base_product_name(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    desktop_dir = home_dir / "Desktop"
    desktop_dir.mkdir(parents=True)
    shortcut_path = desktop_dir / "PyCharm.lnk"
    shortcut_path.write_text("", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.setenv("PUBLIC", str(tmp_path / "public"))

    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("PyCharm 2024.1")

    assert result.ok is True
    assert result.payload is not None
    assert result.payload["matched_target"] == "PyCharm 2024.1"
    assert result.payload["effective_target"] == str(shortcut_path)
    assert result.payload["discovery"]["display_name"] == "PyCharm"
    assert backend.calls[-1][1] == (str(shortcut_path),)


def test_executor_launch_app_accepts_backend_process_verification_even_if_active_window_differs() -> None:
    backend = FakeProcessVerifiedLaunchBackend()
    executor = Executor(backend=backend)

    result = executor.launch_app("steam.exe - 快捷方式")

    assert result.ok is True
    assert result.detail == "launched:steam.exe - 快捷方式"
    assert result.payload is not None
    assert result.payload["status"] == 0
    assert result.payload["pid"] == 27236
    assert result.payload["verification_source"] == "process"
    assert result.payload["verification_hint"] == "steam.exe"
    assert result.payload["target_matches"] is True
    assert result.payload["verification_status"] == "success"
    assert result.payload["result_code"] == "OK"
