"""Aggregate local feedback and optional query logs into a knowledge-gap summary.

Only the question text, mode, reason and latency are read; answers and citations
are never copied. The summary is meant for the weekly human review, not for
automatic training.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SPACE_RE = re.compile(r"\s+")
QUESTION_LIMIT = 90


def _rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _normalize(question: Any) -> str:
    text = SPACE_RE.sub("", str(question or "")).strip()
    return text[:QUESTION_LIMIT]


def collect_gaps(run_root: Path | str | None, *, days: int = 30) -> dict[str, Any]:
    if not run_root:
        return {
            "window_days": days,
            "feedback": {"total": 0, "unhelpful": 0},
            "queries": {"total": 0, "abstained": 0},
            "reasons": {},
            "top_questions": [],
            "note": "run root is unset",
        }
    root = Path(run_root).expanduser().resolve()
    cutoff = datetime.now(UTC) - timedelta(days=days)

    feedback_rows = _rows(root / "feedback.jsonl")
    unhelpful = [row for row in feedback_rows if row.get("helpful") is False]

    query_rows: list[dict[str, Any]] = []
    queries_dir = root / "queries"
    if queries_dir.is_dir():
        for path in sorted(queries_dir.glob("*.jsonl")):
            try:
                day = datetime.fromisoformat(path.stem).replace(tzinfo=UTC)
            except ValueError:
                continue
            if day < cutoff:
                continue
            query_rows.extend(_rows(path))

    reasons = Counter(str(row.get("reason") or "unknown") for row in query_rows)
    abstained = [row for row in query_rows if row.get("abstained")]
    questions = Counter(
        _normalize(row.get("question")) for row in query_rows if row.get("question")
    )
    unhelpful_questions = Counter(
        _normalize(row.get("question")) for row in unhelpful if row.get("question")
    )
    questions.update(unhelpful_questions)

    top = [
        {"question": question, "count": count}
        for question, count in questions.most_common(10)
        if question
    ]
    return {
        "window_days": days,
        "feedback": {"total": len(feedback_rows), "unhelpful": len(unhelpful)},
        "queries": {"total": len(query_rows), "abstained": len(abstained)},
        "reasons": dict(sorted(reasons.items())),
        "top_questions": top,
    }


__all__ = ["collect_gaps"]
