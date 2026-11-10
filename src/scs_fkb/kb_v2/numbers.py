"""Numeric quick reference generated from approved facts at request time."""

from __future__ import annotations

import re
from typing import Any

DIGIT_RE = re.compile(r"\d")
MAX_VALUE_CHARS = 120


def _unit(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "none", "null"} else text


def build_numbers(facts: list[dict[str, Any]], *, limit: int = 80) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for fact in facts:
        if fact.get("status") != "approved":
            continue
        value = str(fact.get("value") or "").strip()
        if not value or not DIGIT_RE.search(value) or len(value) > MAX_VALUE_CHARS:
            continue
        source = fact.get("source") or {}
        doc = str(source.get("doc") or "")
        if not doc:
            continue
        subject = str(fact.get("subject") or "")
        predicate = str(fact.get("predicate") or "")
        key = (doc, str(source.get("section") or ""), subject, predicate, value)
        if key in seen:
            continue
        seen.add(key)
        review_due = str(fact.get("review_due") or "")
        rows.append(
            {
                "topic": str(fact.get("topic") or ""),
                "subject": subject,
                "predicate": predicate,
                "value": value,
                "unit": _unit(fact.get("unit")),
                "doc": doc,
                "section": str(source.get("section") or ""),
                "review_due": review_due,
            }
        )
        if len(rows) >= limit:
            break
    rows.sort(key=lambda row: (row["topic"], row["subject"], row["predicate"]))
    return rows


__all__ = ["build_numbers"]
