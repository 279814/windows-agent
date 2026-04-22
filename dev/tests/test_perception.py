from desktop_agent_dev.perception import DesktopSnapshot, Perception


class FakeBox:
    def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class FakeWindow:
    def __init__(self, name: str, handle: int = 1, process_id: int = 2) -> None:
        self.name = name
        self.handle = handle
        self.process_id = process_id
        self.status = "NORMAL"
        self.bounding_box = FakeBox(0, 0, 100, 100)


class FakeTreeNode:
    def __init__(self, name: str, control_type: str) -> None:
        self.name = name
        self.control_type = control_type
        self.bounding_box = FakeBox(5, 5, 20, 20)


class FakeTreeState:
    def __init__(self) -> None:
        self.interactive_nodes = [FakeTreeNode("Button", "ButtonControl")]
        self.focused_node = type(
            "FocusedNode",
            (),
            {
                "name": "notepad",
                "value": "notepad",
                "text": "notepad",
                "control_type": "Edit",
                "automation_id": "searchBox",
                "class_name": "TextBox",
                "role": "text box",
                "bounding_box": FakeBox(16, 16, 360, 44),
            },
        )()


class FakeState:
    def __init__(self) -> None:
        self.active_window = FakeWindow("Editor")
        self.windows = [FakeWindow("Editor"), FakeWindow("Browser", handle=3, process_id=4)]
        self.cursor_position = (10, 20)
        self.screenshot = b"image"
        self.tree_state = FakeTreeState()


class FakePerceptionBackend:
    def get_state(self, use_vision: bool = False, as_bytes: bool = False):
        return FakeState()

    def get_windows(self):
        return ([FakeWindow("Editor"), FakeWindow("Browser", handle=3, process_id=4)], {1, 3})

    def get_active_window(self):
        return FakeWindow("Editor")


def test_snapshot_returns_stubbed_state() -> None:
    snapshot = Perception().snapshot()
    assert isinstance(snapshot, DesktopSnapshot)
    assert snapshot.metadata["status"] == "stubbed"


def test_snapshot_from_backend() -> None:
    perception = Perception(backend=FakePerceptionBackend())
    snapshot = perception.snapshot(with_screenshot=True)

    assert snapshot.active_window is not None
    assert snapshot.active_window.name == "Editor"
    assert len(snapshot.windows) == 2
    assert snapshot.cursor == (10, 20)
    assert snapshot.screenshot == b"image"
    assert snapshot.tree_nodes[0].name == "Button"
    assert snapshot.focused_control is not None
    assert snapshot.focused_control["name"] == "notepad"
    assert snapshot.focused_control["value"] == "notepad"
    assert snapshot.focused_control["text"] == "notepad"
    assert snapshot.focused_control["window_title"] == "Editor"
