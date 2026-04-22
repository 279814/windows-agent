from desktop_agent_dev.executor import Executor, InputResult


class FakeWindowState:
    def __init__(self, name: str = "main", handle: int | None = 1, status: str = "normal") -> None:
        self.name = name
        self.handle = handle
        self.status = status
        self.window_title = name


class FakeDesktopState:
    def __init__(self, active_window: FakeWindowState | None) -> None:
        self.active_window = active_window


class FakeExecBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._state = FakeDesktopState(FakeWindowState())

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

    def launch_app(self, name: str) -> str:
        self.calls.append(("launch_app", (name,), {}))
        return f"launch:{name}"

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
    assert executor.launch_app("calc").detail == "launch:calc"

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
    assert result.payload["outcome"] in {"success", "success_wm_close_degraded"}
    assert result.payload["post_close_verified"] is True
    assert result.payload["backend_response"] == "close:main"
    assert result.payload["exit_code"] == 0
    assert result.detail
    assert backend.calls[-1][0] == "close_app"
    assert backend.calls[-1][1] == ("main",)


class FakeFailBackend(FakeExecBackend):
    def close_app(self, name: str) -> tuple[str, int]:
        self.calls.append(("close_app", (name,), {}))
        return (f"Failed to close {name}.", 1)


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
