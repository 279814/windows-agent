from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .probe import ProbeResult, run_probe


@dataclass(slots=True)
class HealthcheckResult:
    ok: bool
    probe: ProbeResult
    services: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def run_healthcheck(*, windows_mcp_root: str | Path | None = None, services: dict[str, Any] | None = None) -> HealthcheckResult:
    probe = run_probe(windows_mcp_root)
    service_status: dict[str, bool] = {}
    for name, service in (services or {}).items():
        service_status[name] = service is not None
    ok = probe.ok and all(service_status.values() or [True])
    notes = list(probe.notes)
    for name, available in service_status.items():
        if not available:
            notes.append(f"Service unavailable: {name}")
    return HealthcheckResult(ok=ok, probe=probe, services=service_status, notes=notes)
