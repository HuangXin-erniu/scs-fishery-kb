from __future__ import annotations

from typing import Any

from .answer import CITATION_RE, SENTENCE_RE


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]


def _citation_only(text: str) -> bool:
    return bool(CITATION_RE.search(text)) and not CITATION_RE.sub("", text).strip()


def point_status(answer_text: str, checks: dict[str, Any]) -> tuple[bool, list[str]]:
    """A point is covered only by a sentence that has the terms and a citation."""
    terms = [str(term) for term in checks.get("terms") or []]
    mode = str(checks.get("mode") or "all")
    if not terms:
        return False, []
    missing = [term for term in terms if term not in answer_text]
    sentences = _sentences(answer_text)
    for index, sentence in enumerate(sentences):
        combined = sentence
        look = index + 1
        while look < len(sentences) and _citation_only(sentences[look]):
            combined = f"{combined} {sentences[look]}"
            look += 1
        if not CITATION_RE.search(combined):
            continue
        present = [term in combined for term in terms]
        if (mode == "any" and any(present)) or (mode != "any" and all(present)):
            return True, []
    return False, missing


def coverage_report(
    gold: dict[str, Any],
    checks: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic, evaluation-only per-point coverage for the anchor set."""
    questions: dict[str, Any] = {}
    total_points = 0
    total_covered = 0
    for result in results:
        if result.get("kind") != "answerable":
            continue
        question_id = str(result.get("id"))
        entry = gold.get(question_id) or {}
        points = entry.get("points") or []
        if not points:
            continue
        answer = result.get("answer") or {}
        answer_text = str(answer.get("answer") or "")
        point_checks = {int(item.get("point", -1)): item for item in checks.get(question_id) or []}
        missing_points: list[dict[str, Any]] = []
        covered = 0
        for index, point in enumerate(points):
            status, missing_terms = point_status(answer_text, point_checks.get(index, {}))
            if status:
                covered += 1
                continue
            missing_points.append(
                {
                    "point": index,
                    "missing_terms": missing_terms,
                    "reason": "no_cited_sentence" if missing_terms else "no_citation",
                    "text": str(point),
                }
            )
        questions[question_id] = {
            "points": len(points),
            "covered": covered,
            "rate": round(covered / len(points), 4),
            "missing": missing_points,
        }
        total_points += len(points)
        total_covered += covered
    return {
        "questions": questions,
        "summary": {
            "questions": len(questions),
            "points": total_points,
            "covered": total_covered,
            "rate": round(total_covered / total_points, 4) if total_points else 0.0,
        },
    }


__all__ = ["coverage_report", "point_status"]
