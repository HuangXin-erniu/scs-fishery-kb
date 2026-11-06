#!/usr/bin/env python3
"""Regression report for the v2 retriever on the reviewed 48-question set."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.retrieve_v2 import build_retriever, plan_query


def _question_texts(path: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| Q-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0].startswith("Q-"):
            texts[cells[0]] = cells[2]
    return texts


def _match(hit: Any, anchor: dict[str, Any]) -> bool:
    if hit.chunk.doc_id != anchor.get("doc"):
        return False
    if anchor.get("page") and hit.chunk.page != int(anchor["page"]):
        return False
    if anchor.get("section") and not hit.chunk.section.startswith(str(anchor["section"])):
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--eval-config", default="configs/eval.yaml")
    parser.add_argument("--questions", default="docs/questions.md")
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument(
        "--rerank", action="store_true", help="enable the BGE reranker (default off)"
    )
    parser.add_argument("--report", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    eval_path = Path(args.eval_config)
    if not eval_path.is_absolute():
        eval_path = REPO_ROOT / eval_path
    questions_path = Path(args.questions)
    if not questions_path.is_absolute():
        questions_path = REPO_ROOT / questions_path
    config = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
    pipeline = yaml.safe_load((REPO_ROOT / "configs" / "pipeline.yaml").read_text(encoding="utf-8"))
    answer = pipeline.get("answer") or {}
    min_score = float(answer.get("min_score", 19.0))
    min_matched = int(answer.get("min_matched", 3))
    questions = _question_texts(questions_path)
    retriever = build_retriever(
        Path(args.data_root),
        model_name=args.model,
        reranker=args.rerank,
    )
    meta = config.get("meta") or {}
    anchors = config.get("anchors") or {}
    abstention = config.get("abstention") or []
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for qid, q_anchors in anchors.items():
        question = questions.get(qid, "")
        if not question:
            continue
        plan = plan_query(question)
        started = time.perf_counter()
        hits = retriever.search(question, top_k=5, filters=plan.filters, rerank=args.rerank)
        latency = (time.perf_counter() - started) * 1000
        latencies.append(latency)
        rank = None
        for position, hit in enumerate(hits, start=1):
            if any(_match(hit, anchor) for anchor in q_anchors):
                rank = position
                break
        rows.append(
            {
                "id": qid,
                "split": (meta.get(qid) or {}).get("split", "dev"),
                "hit": rank is not None,
                "rank": rank,
                "gate_ok": retriever.gate_ok(question, min_score, min_matched),
                "latency_ms": round(latency, 1),
            }
        )
    abstained: list[dict[str, Any]] = []
    for qid in abstention:
        question = questions.get(qid, "")
        if not question:
            continue
        abstained.append(
            {
                "id": qid,
                "split": (meta.get(qid) or {}).get("split", "dev"),
                "abstained": not retriever.gate_ok(question, min_score, min_matched),
            }
        )
    for split in ("dev", "test", "all"):
        subset = rows if split == "all" else [row for row in rows if row["split"] == split]
        if not subset:
            continue
        hit_count = sum(1 for row in subset if row["hit"])
        mrr = sum(1.0 / row["rank"] for row in subset if row["rank"]) / len(subset)
        false_refusals = sum(1 for row in subset if not row["gate_ok"])
        print(
            f"{split}: {hit_count}/{len(subset)} anchors, "
            f"MRR {mrr:.4f}, false refusals {false_refusals}"
        )
    p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0.0
    abstained_count = sum(1 for row in abstained if row["abstained"])
    print(f"latency P95 {p95:.1f} ms, abstention {abstained_count}/{len(abstained)}")
    if args.run_root or args.report:
        path = (
            Path(args.report)
            if args.report
            else Path(args.run_root).expanduser() / "P10-IDX-139" / "regression.md"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# P10-IDX-139 retrieval regression",
            "",
            f"- Questions with anchors: {len(rows)}",
            f"- Abstention tests: {len(abstained)}",
            f"- Model: `{args.model}` (rerank={args.rerank})",
            f"- P95 latency: {p95:.1f} ms",
            "",
            "| Split | Anchors | MRR | False refusals |",
            "|---|---:|---:|---:|",
        ]
        for split in ("dev", "test", "all"):
            subset = rows if split == "all" else [row for row in rows if row["split"] == split]
            if not subset:
                continue
            hit_count = sum(1 for row in subset if row["hit"])
            mrr = sum(1.0 / row["rank"] for row in subset if row["rank"]) / len(subset)
            false_refusals = sum(1 for row in subset if not row["gate_ok"])
            lines.append(f"| {split} | {hit_count}/{len(subset)} | {mrr:.4f} | {false_refusals} |")
        lines += ["", "## Abstention", "", f"- {abstained_count}/{len(abstained)} refused", ""]
        lines += ["", "## Misses", ""]
        lines += [f"- `{row['id']}`" for row in rows if not row["hit"]] or ["- none"]
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
