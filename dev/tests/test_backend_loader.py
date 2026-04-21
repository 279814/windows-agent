from pathlib import Path

from desktop_agent_dev.backend_windows_mcp import load_windows_mcp_desktop, BackendLoadError


def test_missing_backend_raises(tmp_path: Path) -> None:
    try:
        load_windows_mcp_desktop(tmp_path)
    except BackendLoadError as exc:
        assert "service module not found" in str(exc)
    else:
        raise AssertionError("BackendLoadError was not raised")
