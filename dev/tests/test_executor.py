from desktop_agent_dev.executor import Executor, InputResult


class FakeExecBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

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
        return f"close:{name}"

    def resize_app(self, name=None, size=None, loc=None) -> str:
        self.calls.append(("resize_app", (), {"name": name, "size": size, "loc": loc}))
        return f"resize:{name}"

    def launch_app(self, name: str) -> str:
        self.calls.append(("launch_app", (name,), {}))
        return f"launch:{name}"


def test_executor_stubs_return_values() -> None:
    executor = Executor()
    assert executor.click(10, 20).detail == "clicked:10,20:left:1"
    assert executor.type_text("abc").detail == "typed:abc"


def test_executor_uses_backend_for_input() -> None:
    backend = FakeExecBackend()
    executor = Executor(backend=backend)

    assert executor.click(100, 200, button="right", clicks=2) == InputResult(
        action="click", ok=True, detail="clicked:100,200:right:2", tool="input_click"
    )
    assert executor.move(9, 8).detail == "moved:9,8"
    assert executor.type_text("hello", press_enter=True, clear=True, caret_position="end").detail == "typed:hello:enter"
    assert executor.shortcut("ctrl+s").detail == "shortcut:ctrl+s"
    assert executor.scroll("down", amount=3).detail == "scrolled:down:3"
    assert executor.multi_select([(1, 2), (3, 4)], press_ctrl=True).detail == "multi_selected:2:ctrl"
    assert executor.multi_edit([(1, 2, "a"), (3, 4, "b")]).detail == "multi_edited:2"
    assert executor.switch_window("main").detail == "switch:main"
    assert executor.focus_window("main").detail == "focus:main"
    assert executor.close_window("main").detail == "close:main"
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
