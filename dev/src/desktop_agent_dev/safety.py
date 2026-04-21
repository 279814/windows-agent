from __future__ import annotations


class SafetyGate:
    def __init__(self) -> None:
        self.mode = "controlled"

    def check(self, action: str) -> bool:
        if self.mode == "observe-only":
            return action in {"observe", "snapshot", "screenshot"}
        return True
