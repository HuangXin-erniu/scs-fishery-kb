#!/usr/bin/env python3
"""Build the Track B (industry-standard) evaluation dataset skeleton.

The private 512-question instrument is read from
``$SCS_FKB_DATA_ROOT/eval/acceptance`` and never modified.  This script writes
three JSONL splits plus a manifest under ``$SCS_FKB_DATA_ROOT/eval/industry``:

* ``retrieval.jsonl``  - 200 frozen rows + 100 placeholders
* ``generation.jsonl`` - 120 frozen rows + 80 placeholders
* ``abstention.jsonl`` - 70 frozen rows + 30 placeholders

Placeholders are filled from the practical-source batches in Phase 3.  The
script prints aggregate counts only; it never prints a question or a gold
answer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.eval_industry import (
    build_dataset,
    manifest,
    resolve_gold_docs,
    write_dataset,
)
from scs_fkb.eval_industry.dataset import sha256_file

SPLITS = ("retrieval", "generation", "abstention")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_doc_map(path: Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mapping = data.get("mapping") if isinstance(data, dict) else None
    if not isinstance(mapping, dict) or not mapping:
        raise SystemExit(f"doc map is empty or malformed: {path}")
    return {str(key): value for key, value in mapping.items()}


def _indexed_docs(path: Path) -> set[str]:
    docs = _read_jsonl(path)
    return {str(row["doc_id"]) for row in docs if row.get("doc_id")}


def _resolution_stats(
    rows: list[dict[str, Any]],
    mapping: dict[str, dict[str, Any]],
    indexed: set[str],
) -> dict[str, int]:
    answerable = [row for row in rows if row.get("answerability") in {"可答", "部分可答"}]
    return {
        "rows": len(rows),
        "answerable_or_partial": len(answerable),
        "resolvable_answerable": sum(
            1 for row in answerable if resolve_gold_docs(row, mapping, indexed)
        ),
        "refusal": sum(1 for row in rows if row.get("answerability") == "应拒答"),
    }


def _report(
    *,
    seed: int,
    stats: dict[str, int],
    manifest_data: dict[str, Any],
    source_hashes: dict[str, str],
) -> str:
    lines = [
        "# Track B dataset skeleton",
        "",
        f"- Seed: `{seed}`",
        f"- Source rows: {stats['rows']}",
        f"- Answerable/partial rows: {stats['answerable_or_partial']}",
        f"- Resolvable answerable/partial rows: {stats['resolvable_answerable']}",
        f"- Must-refuse rows: {stats['refusal']}",
        "",
        "| Split | Total | Frozen | Pending source | Required core |",
        "|---|---:|---:|---:|---:|",
    ]
    for split in SPLITS:
        counts = manifest_data["counts"][split]
        lines.append(
            f"| {split} | {counts['total']} | {counts['frozen']} | "
            f"{counts['pending_source']} | {counts['required_core']} |"
        )
    lines.extend(
        [
            "",
            f"- Gate ready: `{manifest_data['gate_ready']}`",
            f"- Acceptance dataset sha256: `{source_hashes.get('acceptance_dataset', '')}`",
            f"- Doc map sha256: `{source_hashes.get('doc_map', '')}`",
            f"- Indexed documents sha256: `{source_hashes.get('indexed_documents', '')}`",
            "",
            "Placeholders are filled from the practical-source batches in Phase 3. "
            "The frozen core is drawn from the private acceptance instrument; no "
            "question or gold answer appears in the public tree.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--acceptance-dir", default=None)
    parser.add_argument("--dataset-dir", default=None)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    root = Path(args.data_root).expanduser().resolve()
    acceptance = (
        Path(args.acceptance_dir).expanduser().resolve()
        if args.acceptance_dir
        else root / "eval" / "acceptance"
    )
    dataset_dir = (
        Path(args.dataset_dir).expanduser().resolve()
        if args.dataset_dir
        else root / "eval" / "industry"
    )
    dataset_path = acceptance / "dataset.jsonl"
    doc_map_path = acceptance / "doc-map.yaml"
    if not dataset_path.is_file() or not doc_map_path.is_file():
        print(f"error: acceptance dataset missing under {acceptance}", file=sys.stderr)
        return 2
    rows = _read_jsonl(dataset_path)
    mapping = _read_doc_map(doc_map_path)
    indexed_path = root / "v2" / "processed" / "documents.jsonl"
    if not indexed_path.is_file():
        print(f"error: indexed documents missing: {indexed_path}", file=sys.stderr)
        return 2
    indexed = _indexed_docs(indexed_path)
    stats = _resolution_stats(rows, mapping, indexed)
    splits = build_dataset(rows, mapping, indexed, seed=args.seed)
    source_hashes = {
        "acceptance_dataset": sha256_file(dataset_path),
        "doc_map": sha256_file(doc_map_path),
        "indexed_documents": sha256_file(indexed_path),
    }
    if args.write:
        result = write_dataset(
            dataset_dir,
            splits,
            seed=args.seed,
            source_hashes=source_hashes,
            extra={
                "acceptance_dir": "eval/acceptance",
                "indexed_documents": len(indexed),
                "resolution": stats,
            },
        )
    else:
        result = manifest(dataset_dir, seed=args.seed, source_hashes=source_hashes)
    report = _report(seed=args.seed, stats=stats, manifest_data=result, source_hashes=source_hashes)
    if args.report:
        path = Path(args.report).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
    if args.json:
        print(json.dumps({"resolution": stats, "manifest": result}, ensure_ascii=False, indent=2))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
