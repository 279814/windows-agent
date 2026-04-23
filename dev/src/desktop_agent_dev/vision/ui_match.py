from __future__ import annotations

from collections.abc import Sequence

from ..perception import DesktopSnapshot, TreeNodeInfo
from .models import UIMatchCandidate, UIMatchResult


def _normalize(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _score_field(expected: str | None, actual: str | None, *, exact_weight: float, partial_weight: float) -> tuple[float, str | None]:
    if expected is None:
        return 0.0, None
    normalized_expected = _normalize(expected)
    normalized_actual = _normalize(actual)
    if not normalized_expected or not normalized_actual:
        return 0.0, None
    if normalized_expected == normalized_actual:
        return exact_weight, f"exact:{normalized_expected}"
    if normalized_expected in normalized_actual:
        return partial_weight, f"partial:{normalized_expected}"
    return 0.0, None


def match_ui_nodes(
    nodes: Sequence[TreeNodeInfo],
    *,
    name: str | None = None,
    control_type: str | None = None,
    automation_id: str | None = None,
    class_name: str | None = None,
    role: str | None = None,
    window_title: str | None = None,
    min_score: float = 0.5,
) -> UIMatchResult:
    weighted_total = 1.0
    candidates: list[UIMatchCandidate] = []

    for index, node in enumerate(nodes):
        score = 0.0
        reasons: list[str] = []
        for current_score, reason in (
            _score_field(name, node.name, exact_weight=0.35, partial_weight=0.2),
            _score_field(control_type, node.control_type, exact_weight=0.2, partial_weight=0.1),
            _score_field(automation_id, node.automation_id, exact_weight=0.25, partial_weight=0.15),
            _score_field(class_name, node.class_name, exact_weight=0.1, partial_weight=0.05),
            _score_field(role, node.role, exact_weight=0.05, partial_weight=0.03),
            _score_field(window_title, node.window_title, exact_weight=0.05, partial_weight=0.03),
        ):
            score += current_score
            if reason:
                reasons.append(reason)

        normalized = min(score / weighted_total, 1.0)
        if normalized < min_score:
            continue
        candidates.append(
            UIMatchCandidate(
                node_index=index,
                score=round(normalized, 4),
                reasons=tuple(reasons),
                name=node.name,
                control_type=node.control_type,
                automation_id=node.automation_id,
                class_name=node.class_name,
                role=node.role,
                window_title=node.window_title,
                bounds=node.bounds,
                metadata={"process_id": node.process_id, "source": node.source},
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return UIMatchResult(
        candidates=candidates,
        metadata={
            "filters": {
                "name": name,
                "control_type": control_type,
                "automation_id": automation_id,
                "class_name": class_name,
                "role": role,
                "window_title": window_title,
            },
            "min_score": min_score,
        },
    )


def match_snapshot_ui(snapshot: DesktopSnapshot, **filters: str | float | None) -> UIMatchResult:
    return match_ui_nodes(snapshot.tree_nodes, **filters)
