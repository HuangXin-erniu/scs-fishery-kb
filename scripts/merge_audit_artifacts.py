#!/usr/bin/env python3
"""Merge product-path audit artifacts, dedupe by id and add inline citations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CITATION_RE = re.compile(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]")


def _load(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, help="dataset JSONL with ids")
    parser.add_argument("--answers", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    question_ids = [str(row["id"]) for row in _load(Path(args.questions))]
    merged: dict[str, dict] = {}
    for answer_path in args.answers:
        for row in _load(Path(answer_path)):
            merged[str(row.get("id", ""))] = row
    rows: list[dict] = []
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
    out = Path(args.out)
    out.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    missing = len(question_ids) - len(rows)
    print(f"questions={len(question_ids)} merged={len(rows)} missing={missing} -> {out}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
