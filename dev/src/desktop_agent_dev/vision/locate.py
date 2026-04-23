from __future__ import annotations

from collections.abc import Iterable

from ..perception import DesktopSnapshot
from .models import LocateCandidate, LocateResult, OCRResult


def _normalize(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _score_text(query: str, value: str | None) -> float:
    normalized_query = _normalize(query)
    normalized_value = _normalize(value)
    if not normalized_query or not normalized_value:
        return 0.0
    if normalized_query == normalized_value:
        return 1.0
    if normalized_query in normalized_value:
        return 0.9
    query_tokens = set(normalized_query.split())
    value_tokens = set(normalized_value.split())
    if not query_tokens or not value_tokens:
        return 0.0
    overlap = len(query_tokens & value_tokens) / len(query_tokens)
    return round(overlap * 0.7, 4)


def _metadata_candidates(query: str, snapshot: DesktopSnapshot | None) -> Iterable[LocateCandidate]:
    if snapshot is None:
        return []

    candidates: list[LocateCandidate] = []
    focused = snapshot.focused_control or {}
    focused_text = focused.get("text") or focused.get("name")
    focused_score = _score_text(query, focused_text)
    if focused_score > 0:
        candidates.append(
            LocateCandidate(
                text=str(focused_text),
                score=focused_score,
                source="focused_control",
                bounds=focused.get("bounds"),
                metadata={"control_type": focused.get("control_type")},
            )
        )

    for index, node in enumerate(snapshot.tree_nodes):
        score = _score_text(query, node.name)
        if score <= 0:
            continue
        candidates.append(
            LocateCandidate(
                text=node.name,
                score=max(score - 0.05, 0.0),
                source="tree_node",
                bounds=node.bounds,
                metadata={
                    "node_index": index,
                    "control_type": node.control_type,
                    "automation_id": node.automation_id,
                    "window_title": node.window_title,
                },
            )
        )

    if snapshot.active_window is not None:
        score = _score_text(query, snapshot.active_window.name)
        if score > 0:
            candidates.append(
                LocateCandidate(
                    text=snapshot.active_window.name,
                    score=max(score - 0.1, 0.0),
                    source="active_window",
                    bounds=snapshot.active_window.bounds,
                )
            )
    return candidates


def locate_text(
    query: str,
    *,
    ocr_result: OCRResult | None = None,
    snapshot: DesktopSnapshot | None = None,
    min_score: float = 0.5,
) -> LocateResult:
    candidates: list[LocateCandidate] = []
    if ocr_result is not None:
        for span in ocr_result.spans:
            score = _score_text(query, span.text)
            if score < min_score:
                continue
            candidates.append(
                LocateCandidate(
                    text=span.text,
                    score=score,
                    source="ocr",
                    bounds=span.bounds,
                    capture_id=ocr_result.capture_id,
                    metadata={"confidence": span.confidence},
                )
            )

    candidates.extend(candidate for candidate in _metadata_candidates(query, snapshot) if candidate.score >= min_score)
    candidates.sort(key=lambda item: item.score, reverse=True)
    strategy = "ocr-first" if ocr_result is not None else "metadata-only"
    return LocateResult(query=query, strategy=strategy, candidates=candidates, metadata={"min_score": min_score})
