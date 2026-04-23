from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .healthcheck import HealthcheckResult, run_healthcheck
from .probe import ProbeResult, run_probe


@dataclass(slots=True)
class BootstrapResult:
    ok: bool
    probe: ProbeResult
    healthcheck: HealthcheckResult
    actions: list[str] = field(default_factory=list)


class InstallerService:
    """Phase 2 installation/probe helper."""

    def __init__(self, windows_mcp_root: str | Path | None = None) -> None:
        self.windows_mcp_root = Path(windows_mcp_root) if windows_mcp_root else None

    def probe(self) -> ProbeResult:
        return run_probe(self.windows_mcp_root)

    def healthcheck(self, *, services: dict[str, object] | None = None) -> HealthcheckResult:
        return run_healthcheck(windows_mcp_root=self.windows_mcp_root, services=services)

    def bootstrap(self, *, services: dict[str, object] | None = None) -> BootstrapResult:
        probe = self.probe()
        actions = ["validate runtime", "validate backend path", "run healthcheck"]
        health = self.healthcheck(services=services)
        return BootstrapResult(ok=probe.ok and health.ok, probe=probe, healthcheck=health, actions=actions)
