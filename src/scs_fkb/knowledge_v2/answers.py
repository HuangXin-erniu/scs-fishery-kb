"""Canonical answers: reviewed question/answer pairs with resolved evidence.

The answer bank is a fast path for recurring questions. It never replaces a
citation: every entry carries the document and section that supports it, and the
normal citation validator still resolves the answer.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ..config import REPO_ROOT

DEFAULT_ANSWERS = REPO_ROOT / "configs" / "knowledge" / "answers.yaml"
ANSWER_ID = re.compile(r"ANS-\d{3}")
PERSONAS = frozenset({"captain", "crew", "owner", "enforcement", "extension", "general"})
STATUSES = frozenset({"draft", "approved", "retired"})


class AnswerBankError(RuntimeError):
    """Raised when a canonical-answer file is malformed."""


def load_answers(path: Path | str = DEFAULT_ANSWERS) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise AnswerBankError(f"canonical answers not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    entries = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise AnswerBankError(f"answers is not a list: {source}")
    return entries


def _tokens(text: str) -> set[str]:
    clean = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", str(text))
    bigrams = {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}
    latin = set(re.findall(r"[A-Za-z0-9]{2,}", str(text)))
    return bigrams | latin


def validate_answers(
    entries: list[dict[str, Any]],
    *,
    registry: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    seen_questions: set[str] = set()
    for entry in entries:
        identifier = str(entry.get("id") or "<unknown>")
        if not ANSWER_ID.fullmatch(identifier):
            errors.append(f"{identifier}: id must match ANS-<NNN>")
        if identifier in seen:
            errors.append(f"{identifier}: duplicate id")
        seen.add(identifier)
        question = str(entry.get("question") or "").strip()
        if not question:
            errors.append(f"{identifier}: missing question")
        elif question in seen_questions:
            errors.append(f"{identifier}: duplicate question")
        seen_questions.add(question)
        if not str(entry.get("answer") or "").strip():
            errors.append(f"{identifier}: missing answer")
        persona = entry.get("persona")
        if persona is not None and persona not in PERSONAS:
            errors.append(f"{identifier}: persona {persona!r} not in {sorted(PERSONAS)}")
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"{identifier}: status {status!r} not in {sorted(STATUSES)}")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{identifier}: evidence must be a non-empty list")
            continue
        for index, item in enumerate(evidence, start=1):
            if not isinstance(item, dict):
                errors.append(f"{identifier}: evidence {index} is not a mapping")
                continue
            doc = str(item.get("doc") or "")
            if not doc:
                errors.append(f"{identifier}: evidence {index} has no doc")
            elif registry is not None and doc not in registry:
                errors.append(f"{identifier}: evidence {index} doc {doc!r} is not registered")
            if not str(item.get("quote") or "").strip():
                errors.append(f"{identifier}: evidence {index} has no quote")
        source = entry.get("source")
        if not isinstance(source, dict) or not str(source.get("id") or "").strip():
            errors.append(f"{identifier}: missing source")
    return errors


def build_from_faq(faq: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert approved FAQ entries into canonical answers with their evidence."""
    answers: list[dict[str, Any]] = []
    for index, entry in enumerate(faq, start=1):
        if entry.get("status") != "approved":
            continue
        evidence = [
            {
                "doc": str(citation.get("doc") or ""),
                "section": str(citation.get("section") or ""),
                "quote": str(citation.get("quote") or ""),
            }
            for citation in entry.get("citations") or []
            if isinstance(citation, dict)
        ]
        answers.append(
            {
                "id": f"ANS-{index:03d}",
                "question": str(entry.get("question") or ""),
                "aliases": [str(item) for item in entry.get("variants") or []],
                "persona": str(entry.get("persona") or "general"),
                "answer": str(entry.get("answer") or ""),
                "evidence": evidence,
                "source": {"kind": "faq", "id": str(entry.get("id") or "")},
                "status": "approved",
            }
        )
    return answers


def search_answers(
    entries: list[dict[str, Any]],
    question: str,
    *,
    min_overlap: int = 2,
) -> dict[str, Any] | None:
    """Return the best approved canonical answer by token overlap, if any."""
    target = _tokens(question)
    if not target:
        return None
    best: tuple[int, dict[str, Any]] | None = None
    for entry in entries:
        if entry.get("status") != "approved":
            continue
        score = len(target & _tokens(entry.get("question") or ""))
        for alias in entry.get("aliases") or []:
            score = max(score, len(target & _tokens(alias)))
        if score >= min_overlap and (best is None or score > best[0]):
            best = (score, entry)
    return best[1] if best else None


def write_answers(entries: list[dict[str, Any]], path: Path | str = DEFAULT_ANSWERS) -> None:
    payload = {"schema_version": 1, "updated_at": "2026-11-12", "answers": entries}
    Path(path).write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


__all__ = [
    "ANSWER_ID",
    "DEFAULT_ANSWERS",
    "PERSONAS",
    "STATUSES",
    "AnswerBankError",
    "build_from_faq",
    "load_answers",
    "search_answers",
    "validate_answers",
    "write_answers",
]
