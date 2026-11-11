#!/usr/bin/env python3
"""Retrieval regression gate over the public question set.

Reports anchor Recall@5 and MRR and compares them with
``configs/eval-baseline.yaml``. It reads no private instrument and needs the
local index only, so it is a local gate rather than a CI job.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.retrieve_v2 import build_retriever


def _rows(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"empty question set: {path}")
    return [row for row in entries if row.get("type") != "abstain"]


def _match(doc_id: str, row: dict) -> bool:
    if doc_id in set(row.get("expected_docs") or []):
        return True
    prefix = str(row.get("expected_prefix") or "")
    return bool(prefix) and doc_id.startswith(prefix)


def _reachable(row: dict, indexed_docs: set[str]) -> bool:
    """A row is measurable by corpus retrieval only if its expected document is indexed."""
    if any(doc in indexed_docs for doc in row.get("expected_docs") or []):
        return True
    prefix = str(row.get("expected_prefix") or "")
    return bool(prefix) and any(doc.startswith(prefix) for doc in indexed_docs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--set", default=str(REPO_ROOT / "configs" / "eval-public.yaml"))
    parser.add_argument("--baseline", default=str(REPO_ROOT / "configs" / "eval-baseline.yaml"))
    parser.add_argument("--tolerance", type=float, default=0.02)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--rerank", action="store_true", help="enable the cross-encoder")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2

    rows = _rows(Path(args.set))
    retriever = build_retriever(args.data_root, reranker=args.rerank)
    indexed_docs = {str(chunk.doc_id) for chunk in getattr(retriever, "chunks", []) or []}
    reachable = [row for row in rows if _reachable(row, indexed_docs)]
    unreachable = [
        str(row.get("id") or row["question"]) for row in rows if not _reachable(row, indexed_docs)
    ]
    hits = 0
    all_hits = 0
    reciprocal = 0.0
    all_reciprocal = 0.0
    misses: list[str] = []
    latencies: list[float] = []
    for row in rows:
        started = time.perf_counter()
        found = retriever.search(str(row["question"]), top_k=5, rerank=args.rerank)
        latencies.append((time.perf_counter() - started) * 1000)
        docs = [hit.chunk.doc_id for hit in found]
        rank = next((index for index, doc in enumerate(docs, start=1) if _match(doc, row)), None)
        if rank is not None:
            all_hits += 1
            all_reciprocal += 1.0 / rank
            if _reachable(row, indexed_docs):
                hits += 1
                reciprocal += 1.0 / rank
        elif _reachable(row, indexed_docs):
            misses.append(str(row.get("id") or row["question"]))
    metrics = {
        "questions": len(rows),
        "reachable_questions": len(reachable),
        "unreachable": unreachable,
        "recall_at_5": round(hits / len(reachable), 4) if reachable else 0.0,
        "mrr": round(reciprocal / len(reachable), 4) if reachable else 0.0,
        "recall_at_5_all": round(all_hits / len(rows), 4) if rows else 0.0,
        "mrr_all": round(all_reciprocal / len(rows), 4) if rows else 0.0,
        "misses": misses,
        "set": Path(args.set).name,
        "rerank": args.rerank,
        "p50_ms": round(statistics.median(latencies), 1) if latencies else 0.0,
        "p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1)
        if latencies
        else 0.0,
    }
    current = Path(args.data_root).expanduser() / "v2" / "index" / "current.json"
    if current.is_file():
        try:
            metrics["index_version"] = json.loads(current.read_text(encoding="utf-8")).get(
                "index_version"
            )
        except json.JSONDecodeError:
            pass

    baseline_path = Path(args.baseline)
    if args.write_baseline:
        baseline_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "updated_at": date.today().isoformat(),
                    "recall_at_5": metrics["recall_at_5"],
                    "mrr": metrics["mrr"],
                    "recall_at_5_all": metrics["recall_at_5_all"],
                    "mrr_all": metrics["mrr_all"],
                    "tolerance": args.tolerance,
                    "questions": metrics["questions"],
                    "reachable_questions": metrics["reachable_questions"],
                    "note": "recall_at_5 and mrr cover rows whose expected document is indexed",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        metrics["baseline_written"] = str(baseline_path)
    elif baseline_path.is_file():
        baseline = yaml.safe_load(baseline_path.read_text(encoding="utf-8")) or {}
        floor_recall = float(baseline.get("recall_at_5") or 0.0) - args.tolerance
        floor_mrr = float(baseline.get("mrr") or 0.0) - args.tolerance
        metrics["baseline"] = {
            "recall_at_5": baseline.get("recall_at_5"),
            "mrr": baseline.get("mrr"),
            "updated_at": baseline.get("updated_at"),
        }
        metrics["passed"] = args.rerank or (
            metrics["recall_at_5"] >= floor_recall and metrics["mrr"] >= floor_mrr
        )

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(
            f"recall@5 {metrics['recall_at_5']} MRR {metrics['mrr']} "
            f"questions {metrics['reachable_questions']}/{metrics['questions']} "
            f"unreachable {len(unreachable)} misses {len(misses)} "
            f"(all rows {metrics['recall_at_5_all']} / {metrics['mrr_all']})"
        )
        if metrics.get("passed") is False:
            print("regression: below the recorded baseline", file=sys.stderr)
    return 0 if metrics.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
