#!/usr/bin/env python3
"""Term-level evidence audit: which rubric terms the indexed clauses can support."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from scs_fkb.eval_accept.points import (
    ConceptSource,
    PointOverrides,
    point_specs,
    rule_for,
    rule_pattern,
)


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("set --data-root or SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    root = Path(args.data_root).expanduser().resolve()
    dataset = _load(root / "eval/acceptance/dataset.jsonl")
    chunks = _load(root / "v2/processed/chunks.jsonl")

    concepts = ConceptSource.load("configs/terms.yaml", root / "eval/acceptance/domain-terms.yaml")
    overrides = PointOverrides.load(root / "eval/acceptance/point-overrides.yaml")
    text = " ".join(chunk["text"] for chunk in chunks)

    total = supported = 0
    by_doc: Counter[str] = Counter()
    by_domain: Counter[str] = Counter()
    uncovered_examples: list[dict] = []
    for row in dataset:
        if row["answerability"] not in ("可答", "部分可答"):
            continue
        for index, spec in enumerate(point_specs(row, concepts=concepts, overrides=overrides)):
            override = overrides.get(row["id"], index)
            if override:
                terms, pattern = list(override.terms), ""
            elif spec.terms:
                terms, pattern = list(spec.terms), ""
            elif spec.rule:
                terms, pattern = [], rule_pattern(spec.rule) or ""
            elif rule_for(row["required_points"][index]):
                terms, pattern = [], rule_pattern(rule_for(row["required_points"][index])) or ""
            else:
                continue
            total += 1
            ok = (
                all(term in text for term in terms)
                if terms
                else bool(pattern and re.search(pattern, text))
            )
            if ok:
                supported += 1
                continue
            by_domain[row["domain"]] += 1
            for source_id in row["scs_doc_ids"]:
                by_doc[source_id] += 1
            if len(uncovered_examples) < 40:
                uncovered_examples.append(
                    {
                        "id": row["id"],
                        "point": row["required_points"][index],
                        "terms": terms or pattern,
                        "expected": row["scs_doc_ids"],
                    }
                )

    summary = {
        "chunks": len(chunks),
        "documents": len({chunk["doc_id"] for chunk in chunks}),
        "points_total": total,
        "points_supported": supported,
        "ceiling": round(supported / total, 4) if total else None,
        "gap_points": total - supported,
        "uncovered_by_document": by_doc.most_common(20),
        "uncovered_by_domain": by_domain.most_common(20),
        "uncovered_examples": uncovered_examples[:20],
    }
    out = (
        Path(args.out)
        if args.out
        else Path(os.environ.get("SCS_FKB_RUN_ROOT", ".")) / "P11-CORP-180"
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Term-level evidence audit",
        "",
        f"- Indexed documents: {summary['documents']}; chunks: {summary['chunks']}",
        f"- Judgeable points: {summary['points_total']}",
        f"- Supported by an indexed clause: {summary['points_supported']} ({summary['ceiling']})",
        "",
        "## Uncovered points by missing document",
        "",
        "| Document | Points |",
        "|---|---:|",
    ]
    lines += [f"| {name} | {count} |" for name, count in summary["uncovered_by_document"]]
    lines += ["", "## Uncovered points by domain", "", "| Domain | Points |", "|---|---:|"]
    lines += [f"| {name} | {count} |" for name, count in summary["uncovered_by_domain"]]
    (out / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("points_total", "points_supported", "ceiling")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
