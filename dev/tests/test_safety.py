from desktop_agent_dev.safety import SafetyGate


def test_observe_only_blocks_execution() -> None:
    gate = SafetyGate()
    gate.mode = "observe-only"
    assert gate.check("snapshot") is True
    assert gate.check("click") is False
