#!/usr/bin/env python3
"""Track B retrieval profiles over the private industry set.

Reports recall@5/@10, MRR and nDCG@10 for the shipped default and one or more
evaluation-only profiles. It reads the private dataset under the data root and
writes a report under the run root; no model calls and no register writes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.retrieve_v2 import build_retriever


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise SystemExit(f"missing Track B rows: {path}")
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _gold(row: dict[str, Any]) -> set[str]:
    return {str(item.get("doc_id")) for item in row.get("gold_docs") or [] if item.get("doc_id")}


def _measure(
    retriever: Any,
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    documents: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    retriever.depth = int(profile["depth"])
    retriever.bm25_weight = float(profile["bm25_weight"])
    retriever.dense_weight = float(profile["dense_weight"])
    indexed = {chunk.doc_id for chunk in getattr(retriever, "chunks", []) or []}
    reachable = [row for row in rows if _gold(row) & indexed]
    hit5 = hit10 = 0
    reciprocal = 0.0
    ndcg_first = ndcg_all = 0.0
    latencies: list[float] = []
    for row in reachable:
        started = time.perf_counter()
        hits = retriever.search_fused(str(row["question"]), top_k=50, rerank=False)
        latencies.append((time.perf_counter() - started) * 1000)
        target = _gold(row)
        if profile.get("doc_rerank"):
            from scs_fkb.retrieve_v2.doc_rank import DEFAULT_WEIGHTS, rank_documents

            weights = tuple(profile.get("doc_weights") or DEFAULT_WEIGHTS)
            ranked = rank_documents(
                str(row["question"]),
                hits,
                documents,
                weights=weights,
                top_k=10,
            )
            docs = [doc_id for doc_id, _score in ranked]
        else:
            scores: dict[str, float] = {}
            for hit in hits:
                scores[hit.chunk.doc_id] = scores.get(hit.chunk.doc_id, 0.0) + hit.score
            docs = [
                doc_id for doc_id, _score in sorted(scores.items(), key=lambda item: -item[1])[:10]
            ]
        rank5 = next((index for index, doc in enumerate(docs[:5], start=1) if doc in target), None)
        rank10 = next((index for index, doc in enumerate(docs, start=1) if doc in target), None)
        if rank5:
            hit5 += 1
        if rank10:
            hit10 += 1
            reciprocal += 1.0 / rank10
            ndcg_first += 1.0 / math.log2(rank10 + 1)
        dcg = sum(1.0 / math.log2(index + 2) for index, doc in enumerate(docs) if doc in target)
        idcg = sum(1.0 / math.log2(index + 2) for index in range(min(len(target), 10)))
        ndcg_all += dcg / idcg if idcg else 0.0
    count = len(reachable)
    latencies.sort()
    return {
        "rows": len(rows),
        "reachable": count,
        "recall_at_5": round(hit5 / count, 4) if count else None,
        "recall_at_10": round(hit10 / count, 4) if count else None,
        "mrr_at_10": round(reciprocal / count, 4) if count else None,
        "ndcg_at_10": round(ndcg_first / count, 4) if count else None,
        "ndcg_at_10_first_gold": round(ndcg_first / count, 4) if count else None,
        "ndcg_at_10_all_gold": round(ndcg_all / count, 4) if count else None,
        "oracle_ndcg_at_10": round(hit10 / count, 4) if count else None,
        "p50_ms": round(latencies[len(latencies) // 2], 1) if latencies else None,
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1) if latencies else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--config", default="configs/eval-trackb.yaml")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=__import__("sys").stderr)
        return 2
    root = Path(args.data_root).expanduser().resolve()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    dataset = config.get("dataset") or {}
    rows = _rows(
        root
        / str(dataset.get("dir") or "eval/industry")
        / str(dataset.get("file") or "retrieval.jsonl")
    )
    profiles = config.get("profiles") or {}
    selected = args.profile or list(profiles)
    unknown = [name for name in selected if name not in profiles]
    if unknown:
        print(f"error: unknown profiles: {unknown}", file=__import__("sys").stderr)
        return 2
    retriever = build_retriever(root, reranker=False)
    documents = {row["doc_id"]: row for row in _rows(root / "v2" / "processed" / "documents.jsonl")}
    report = {
        "dataset": str(dataset.get("dir") or "eval/industry"),
        "target_recall_at_10": dataset.get("target_recall_at_10"),
        "profiles": {
            name: _measure(retriever, rows, profiles[name], documents) for name in selected
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.run_root:
        directory = Path(args.run_root).expanduser().resolve() / "P26-PHASE4"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "trackb-profiles.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        lines = ["# Track B retrieval profiles", ""]
        for name, values in report["profiles"].items():
            lines += [
                f"## {name}",
                "",
                f"- recall@5: {values['recall_at_5']}",
                f"- recall@10: {values['recall_at_10']} (target {report['target_recall_at_10']})",
                f"- MRR@10: {values['mrr_at_10']}",
                f"- nDCG@10: {values['ndcg_at_10']}",
                f"- p50/p95: {values['p50_ms']}/{values['p95_ms']} ms",
                "",
            ]
        (directory / "trackb-profiles.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"report: {directory / 'trackb-profiles.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
