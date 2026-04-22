from desktop_agent_dev.executor import Executor, InputResult


class FakeWindowState:
    def __init__(self, name: str = "main", handle: int | None = 1, status: str = "normal") -> None:
        self.name = name
        self.handle = handle
        self.status = status
        self.window_title = name


class FakeDesktopState:
    def __init__(self, active_window: FakeWindowState | None, windows: list[FakeWindowState] | None = None) -> None:
        self.active_window = active_window
        self.windows = windows or ([active_window] if active_window is not None else [])


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
    assert result == InputResult(action="click", ok=True, detail="clicked:100,200:right:2", payload=result.payload, tool="input_click")
    assert executor.move(9, 8).detail == "moved:9,8"
    assert executor.type_text("hello", press_enter=True, clear=True, caret_position="end").detail == "typed:hello:enter"
    assert executor.shortcut("ctrl+s").detail == "shortcut:ctrl+s"
    assert executor.scroll("down", amount=3).detail == "scrolled:down:3"
    assert executor.multi_select([(1, 2), (3, 4)], press_ctrl=True).detail == "multi_selected:2:ctrl"
    assert executor.multi_edit([(1, 2, "a"), (3, 4, "b")]).detail == "multi_edited:2"
    assert executor.switch_window("main").detail == "switch:main"
    assert executor.focus_window("main").detail == "focus:main"
    close_result = executor.close_window("main")
    assert close_result.ok is True
    assert close_result.payload is not None
    assert close_result.payload["post_close_verified"] is True
    assert executor.resize_window(name="main", width=100, height=200).detail == "resize:main"
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
        "close_app",
        "resize_app",
        "launch_app",
    ]


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


def test_hit_test_prefers_more_specific_overlap_candidate() -> None:
    backend = FakeHitBackend()
    executor = Executor(backend=backend)
    result = executor.click(30, 30)

    assert result.payload is not None
    assert result.payload["element"]["name"] == "PrimaryButton"
    assert result.payload["element"]["found"] is True
    assert result.payload["element"]["confidence"] > 0.5
    assert result.payload["element"]["z_index"] == 1


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
