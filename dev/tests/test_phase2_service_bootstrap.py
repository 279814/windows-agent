from __future__ import annotations

from desktop_agent_dev.installer import InstallerService
from desktop_agent_dev.mcp_server import create_server
from desktop_agent_dev.workflow import ArtifactStore, WorkflowCoordinator


def test_phase2_service_slots_exist_without_optional_modules() -> None:
    server = create_server(windows_mcp_root=None)

    assert hasattr(server.services, "workflow")
    assert hasattr(server.services, "installer")
    assert server.services.workflow is not None
    assert server.services.installer is not None


def test_workflow_coordinator_plans_steps() -> None:
    coordinator = WorkflowCoordinator(ArtifactStore())

    result = coordinator.plan(
        {
            "goal": "browser to notepad",
            "steps": [
                {"kind": "observe", "name": "capture source"},
                {"kind": "input", "name": "paste target", "params": {"text": "hello"}},
            ],
        }
    )

    assert result.ok is True
    assert result.status == "planned"
    assert len(result.steps) == 2
    assert result.steps[1]["params"]["text"] == "hello"


def test_installer_probe_and_healthcheck_are_callable() -> None:
    installer = InstallerService()

    probe = installer.probe()
    health = installer.healthcheck(services={"workflow": object()})

    assert isinstance(probe.checks, dict)
    assert "python_supported" in probe.checks
    assert "workflow" in health.services
