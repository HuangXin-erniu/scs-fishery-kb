from __future__ import annotations

import unicodedata
from typing import Any

from .answer import CITATION_RE, SENTENCE_RE


def _norm(value: str) -> str:
    """Fold width and whitespace so full-width digits and split labels compare."""
    return "".join(unicodedata.normalize("NFKC", str(value)).split())


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]


def _citation_only(text: str) -> bool:
    return bool(CITATION_RE.search(text)) and not CITATION_RE.sub("", text).strip()


def _cited_groups(answer_text: str) -> dict[tuple[str, int, str], list[str]]:
    groups: dict[tuple[str, int, str], list[str]] = {}
    sentences = _sentences(answer_text)
    for index, sentence in enumerate(sentences):
        combined = sentence
        look = index + 1
        while look < len(sentences) and _citation_only(sentences[look]):
            combined = f"{combined} {sentences[look]}"
            look += 1
        for doc_id, page, section in CITATION_RE.findall(combined):
            key = (doc_id, int(page) if page else 0, section)
            groups.setdefault(key, []).append(combined)
    return groups


def point_status(answer_text: str, checks: dict[str, Any]) -> tuple[bool, list[str]]:
    """A point is covered by cited text carrying every check term.

    mode=all: every term in one cited sentence;
    mode=any: at least one term in one cited sentence;
    mode=section: every term in cited sentences from the same doc/page/section.
    """
    terms = [_norm(term) for term in checks.get("terms") or []]
    mode = str(checks.get("mode") or "all")
    if not terms:
        return False, []
    answer_norm = _norm(answer_text)
    missing = [term for term in terms if term not in answer_norm]
    if mode == "section":
        for group in _cited_groups(answer_text).values():
            joined = _norm(" ".join(group))
            if all(term in joined for term in terms):
                return True, []
        return False, missing
    sentences = _sentences(answer_text)
    for index, sentence in enumerate(sentences):
        combined = sentence
        look = index + 1
        while look < len(sentences) and _citation_only(sentences[look]):
            combined = f"{combined} {sentences[look]}"
            look += 1
        if not CITATION_RE.search(combined):
            continue
        present = [term in _norm(combined) for term in terms]
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
