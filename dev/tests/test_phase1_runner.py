from __future__ import annotations

from pathlib import Path


def test_phase1_runner_script_exists() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_phase1_tests.py"
    assert script.exists()


def test_phase1_docs_exist() -> None:
    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    assert (docs_dir / "phase1_final_integration_checklist.md").exists()
