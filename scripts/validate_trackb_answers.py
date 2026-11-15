#!/usr/bin/env python3
"""Validate that every citation in an answer exists in its evidence context.

Reads JSONL rows with ``answer`` and ``contexts`` fields; a citation
``[DOC_ID §section]`` must appear verbatim in at least one context label.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CITATION_RE = re.compile(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]")


def _norm(value: str) -> str:
    return re.sub(r"[\s、，,。；;]", "", value.strip())


def _section_matches(cited: str, context: str) -> bool:
    cited_n = _norm(cited)
    context_n = _norm(context)
    if cited_n.startswith("p.") or context_n.startswith("p."):
        return cited_n == context_n
    # A citation may be a shorter article prefix (§三 vs §三、处罚措施), but
    # a different article title (§五、报告要求 vs §五、报告内容) must fail.
    return bool(cited_n) and context_n.startswith(cited_n)


def validate(row: dict) -> list[str]:
    contexts = row.get("contexts") or []
    answer = str(row.get("answer") or "")
    labels: dict[str, list[str]] = {}
    for context in contexts:
        match = re.match(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]", context)
        if match:
            labels.setdefault(match.group(1), []).append(match.group(2))
    bad: list[str] = []
    for doc_id, section in CITATION_RE.findall(answer):
        sections = labels.get(doc_id, [])
        if not any(_section_matches(section.strip(), item) for item in sections):
            bad.append(f"{doc_id} §{section.strip()}")
    return bad


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    path = Path(args.input)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    total = 0
    failures = 0
    for row in rows:
        bad = validate(row)
        total += len(CITATION_RE.findall(str(row.get("answer") or "")))
        if bad:
            failures += 1
            print(f"{row.get('id', '?')}: {', '.join(bad)}")
    print(f"rows={len(rows)} citations={total} rows_with_bad={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
