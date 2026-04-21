from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from desktop_agent_dev.mcp_server import create_server


ROOT = Path(__file__).resolve().parents[1]


class Phase1ValidationError(RuntimeError):
    pass


def run(cmd: list[str]) -> int:
    print(f"[run] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def diff_dict(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    delta: dict[str, Any] = {}
    for key in keys:
        if before.get(key) != after.get(key):
            delta[key] = {"before": before.get(key), "after": after.get(key)}
    return delta


def serialize_snapshot(snapshot: Any) -> dict[str, Any]:
    active_window = asdict(snapshot.active_window) if snapshot.active_window else None
    windows = [asdict(item) for item in snapshot.windows]
    tree_nodes = [asdict(item) for item in snapshot.tree_nodes]
    return {
        "active_window": active_window,
        "windows": windows,
        "cursor": snapshot.cursor,
        "tree_nodes": tree_nodes,
        "metadata": snapshot.metadata,
        "has_screenshot": snapshot.screenshot is not None,
        "screenshot_bytes": len(snapshot.screenshot or b""),
    }


def _safe_call(label: str, fn: Callable[[], Any]) -> Any:
    print(f"[integration] calling {label}")
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        raise Phase1ValidationError(f"{label} failed: {exc}") from exc
    print(f"[integration] {label} ok")
    return result


def _backend_object(server: Any) -> Any:
    bundle = getattr(server, "_backend_bundle", None)
    if bundle is not None:
        return getattr(bundle, "desktop", None)
    return None


def _log_backend_methods(backend: Any) -> None:
    methods = sorted(name for name in dir(backend) if not name.startswith("_") and callable(getattr(backend, name)))
    print(json.dumps({"backend_methods": methods}, ensure_ascii=False, indent=2))


def validate_registry(server: Any) -> None:
    metadata = server.tool_registry.metadata()
    assert metadata["stage"] == "phase1"
    assert "tools" in metadata
    assert "groups" in metadata
    assert "vision_capture" in server.tool_registry.specs
    assert "ocr_extract" in server.tool_registry.specs
    assert metadata["capabilities"]["vision_hooks"] is True
    assert metadata["capabilities"]["ocr_hooks"] is True


def validate_perception(server: Any, backend: Any | None) -> dict[str, Any]:
    print("[integration] perception validation")
    before = serialize_snapshot(_safe_call("perception.snapshot(false)", lambda: server.services.perception.snapshot(with_screenshot=False)))
    after = serialize_snapshot(_safe_call("perception.snapshot(true)", lambda: server.services.perception.snapshot(with_screenshot=True)))
    delta = diff_dict(before, after)
    print(json.dumps({"before": before, "after": after, "delta": delta}, ensure_ascii=False, indent=2))

    if backend is not None:
        _log_backend_methods(backend)
        if hasattr(backend, "get_state"):
            state = _safe_call("backend.get_state", lambda: backend.get_state(use_vision=True, as_bytes=True))
            print(json.dumps({"backend_state_type": type(state).__name__}, ensure_ascii=False, indent=2))
        if hasattr(backend, "get_windows"):
            windows = _safe_call("backend.get_windows", backend.get_windows)
            print(json.dumps({"backend_windows_type": type(windows).__name__}, ensure_ascii=False, indent=2))
        if hasattr(backend, "get_active_window"):
            active = _safe_call("backend.get_active_window", backend.get_active_window)
            print(json.dumps({"backend_active_window_type": type(active).__name__}, ensure_ascii=False, indent=2))

    assert before["metadata"].get("source") in {"stubbed", "windows-mcp"}
    assert after["has_screenshot"] in {True, False}
    return {"before": before, "after": after, "delta": delta}


def validate_executor(server: Any, backend: Any | None) -> dict[str, Any]:
    print("[integration] executor validation")
    results: dict[str, Any] = {
        "click": _safe_call("executor.click", lambda: server.services.executor.click(10, 20)),
        "type": _safe_call("executor.type_text", lambda: server.services.executor.type_text("phase1", press_enter=False, clear=False)),
        "shortcut": _safe_call("executor.shortcut", lambda: server.services.executor.shortcut("ctrl+s")),
    }

    if backend is not None:
        if hasattr(backend, "click"):
            _safe_call("backend.click", lambda: backend.click((10, 20), button="left", clicks=1))
        if hasattr(backend, "type"):
            _safe_call("backend.type", lambda: backend.type((0, 0), text="phase1", press_enter=False, clear=False, caret_position="idle"))
        if hasattr(backend, "shortcut"):
            _safe_call("backend.shortcut", lambda: backend.shortcut("ctrl+s"))
        if hasattr(backend, "switch_app"):
            _safe_call("backend.switch_app", lambda: backend.switch_app("notepad"))
        if hasattr(backend, "resize_app"):
            _safe_call("backend.resize_app", lambda: backend.resize_app(name=None, size=None, loc=None))

    payload = {name: asdict(result) for name, result in results.items()}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    assert results["click"].tool == "input_click"
    assert results["type"].tool == "input_type"
    assert results["shortcut"].tool == "input_shortcut"
    return payload


def validate_task_and_safety(server: Any) -> dict[str, Any]:
    print("[integration] task and safety validation")
    plan = _safe_call("planner.create_plan", lambda: server.services.planner.create_plan("打开记事本并输入 hello"))
    state = _safe_call("safety.check(click)", lambda: server.services.safety.check("click"))
    summary = {
        "plan": {"goal": plan.goal, "steps": [asdict(step) for step in plan.steps]},
        "safety_click_allowed": state,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    assert plan.steps
    return summary


def validate_real_backend(backend_root: str) -> int:
    server = _safe_call("create_server", lambda: create_server(backend_root))
    backend = _backend_object(server)
    print(f"[integration] backend_root={backend_root}")
    print(f"[integration] tools={sorted(server.tool_registry.specs)}")
    validate_registry(server)
    validate_task_and_safety(server)
    perception = validate_perception(server, backend)
    executor = validate_executor(server, backend)

    print("[integration] phase1 integration summary")
    print(json.dumps({"perception": perception, "executor": executor}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase 1 validation checks")
    parser.add_argument("--real-backend-root", default=None)
    parser.add_argument("--skip-integration", action="store_true")
    parser.add_argument("--validate-real-backend", action="store_true")
    args = parser.parse_args()

    if args.validate_real_backend:
        if not args.real_backend_root:
            print("[error] --validate-real-backend requires --real-backend-root")
            return 2
        try:
            return validate_real_backend(args.real_backend_root)
        except Phase1ValidationError as exc:
            print(f"[error] {exc}")
            return 1

    steps: list[list[str]] = [
        [sys.executable, "-m", "pytest"],
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
    ]

    if not args.skip_integration:
        if args.real_backend_root:
            steps.append([sys.executable, "-m", "desktop_agent_dev", "--windows-mcp-root", args.real_backend_root])
        else:
            print("[warn] real backend root not provided; skipping backend launch validation")

    for cmd in steps:
        code = run(cmd)
        if code != 0:
            return code

    if not args.skip_integration and args.real_backend_root:
        try:
            return validate_real_backend(args.real_backend_root)
        except Phase1ValidationError as exc:
            print(f"[error] {exc}")
            return 1

    print("[ok] phase 1 checks completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
