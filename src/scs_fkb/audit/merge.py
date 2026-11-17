"""Merge product-path audit artifacts without dropping cited sections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CITATION_RE = re.compile(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def merge_artifacts(questions_path: Path, answer_paths: list[Path]) -> list[dict[str, Any]]:
    question_ids = [str(row["id"]) for row in load_jsonl(questions_path)]
    merged: dict[str, dict[str, Any]] = {}
    for answer_path in answer_paths:
        for row in load_jsonl(answer_path):
            merged[str(row.get("id", ""))] = row
    rows: list[dict[str, Any]] = []
    for qid in question_ids:
        row = merged.get(qid)
        if row is None:
            continue
        seen = {(c.get("doc_id"), c.get("section")) for c in row.get("citations") or []}
        for doc_id, section in CITATION_RE.findall(row.get("visible_answer", "")):
            key = (doc_id, section.strip())
            if key not in seen:
                seen.add(key)
                row.setdefault("citations", []).append(
                    {"doc_id": doc_id, "section": section.strip()}
                )
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
