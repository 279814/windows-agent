from __future__ import annotations

from dataclasses import dataclass

from windows_mcp.desktop.service import Desktop


@dataclass
class _Window:
    name: str
    process_id: int
    handle: int


@dataclass
class _State:
    windows: list[_Window]


class _FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def children(self, recursive: bool = True) -> list[object]:
        return []

    def name(self) -> str:
        return "pycharm64.exe"

    def exe(self) -> str:
        return r"D:\Develop-Data\pycharm\PyCharm 2024.1\bin\pycharm64.exe"

    def cmdline(self) -> list[str]:
        return [r"D:\Develop-Data\pycharm\PyCharm 2024.1\bin\pycharm64.exe"]
def _desktop_with_state(state: _State) -> Desktop:
    desktop = Desktop.__new__(Desktop)
    desktop.desktop_state = None
    desktop.get_state = lambda use_vision=False, as_bytes=False: state
    return desktop


def test_find_launch_verification_window_matches_alias_from_exe_path() -> None:
    desktop = _desktop_with_state(_State(windows=[_Window(name="微信", process_id=321, handle=10)]))

    window_name, window_pid, source = desktop._find_launch_verification_window(
        r"C:\Program Files\Tencent\WeChat\WeChat.exe",
        pid=0,
        attempts=1,
    )

    assert window_name == "微信"
    assert window_pid == 321
    assert source in {"name", "phrase"}


def test_find_launch_verification_window_accepts_matching_process_when_window_not_ready(monkeypatch) -> None:
    desktop = _desktop_with_state(_State(windows=[]))
    monkeypatch.setattr("windows_mcp.desktop.service.Process", _FakeProcess)

    window_name, window_pid, source = desktop._find_launch_verification_window(
        r"D:\Develop-Data\pycharm\PyCharm 2024.1\bin\pycharm64.exe",
        pid=222,
        known_pids=[222],
        attempts=1,
    )

    assert window_name
    assert window_pid == 222
    assert source == "process"


def test_launch_name_variants_include_jetbrains_product_family() -> None:
    desktop = _desktop_with_state(_State(windows=[]))

    variants = desktop._launch_name_variants(r"D:\Develop-Data\pycharm\PyCharm 2024.1\bin\pycharm64.exe")
    expanded = desktop._expand_launch_aliases(variants)

    assert "pycharm64" in variants
    assert "pycharm" in variants
    assert "jetbrains" in expanded


def test_extract_pid_candidates_reads_successful_launch_results() -> None:
    desktop = _desktop_with_state(_State(windows=[]))

    pids = desktop._extract_pid_candidates(
        "Launched via start menu shortcut: pycharm 2024.1 (score=90). 34032\r\n | unverified:command:foo | 6212"
    )

    assert 34032 in pids
    assert 6212 in pids
