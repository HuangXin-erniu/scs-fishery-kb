#!/usr/bin/env python3
"""Build a 512 audit artifact from the deterministic slot arm (no LLM calls)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.answer_v3.slots import answer_with_slots, split_slots  # noqa: E402
from scs_fkb.audit.schema import AuditRecord  # noqa: E402
from scs_fkb.service_v2.answer import build_service  # noqa: E402

THEME_TERMS = {
    "休渔": ("休渔", "禁渔", "伏季"),
    "证照": ("许可证", "船网工具", "登记", "过户", "证书"),
    "执法": ("处罚", "罚款", "执法", "没收", "立案"),
    "生态": ("保护区", "珊瑚", "海草", "红树林", "生态", "玳瑁", "海龟", "鲎"),
    "预报": ("预报", "渔情", "台风", "厄尔尼诺", "海温", "赤潮"),
    "补贴": ("补贴", "补助", "减船", "油价"),
}


def _theme(question: str) -> str:
    for name, terms in THEME_TERMS.items():
        if any(term in question for term in terms):
            return name
    return "其他"


def _coverage(rows: list[dict], answers: list[dict]) -> dict:
    stats = {"records": len(answers), "slots": 0, "direct": 0, "partial": 0, "gap": 0}
    per_question = []
    for row, answer in zip(rows, answers, strict=True):
        slots = len(split_slots(row["question"]))
        lines = [
            line
            for line in answer["visible_answer"].split("\n")
            if line.startswith(("结论：", "另："))
        ]
        partial = sum(
            1
            for line in answer["visible_answer"].split("\n")
            if line.startswith("缺口：本题问的是")
        )
        direct = len(lines) - partial
        gap = max(0, slots - len(lines))
        stats["slots"] += slots
        stats["direct"] += direct
        stats["partial"] += partial
        stats["gap"] += gap
        per_question.append(
            {
                "id": row["id"],
                "slots": slots,
                "direct": direct,
                "partial": partial,
                "gap": gap,
            }
        )
    stats["total_coverage"] = round(
        (stats["direct"] + stats["partial"]) / max(1, stats["slots"]), 4
    )
    stats["direct_coverage"] = round(stats["direct"] / max(1, stats["slots"]), 4)
    stats["per_question"] = per_question
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--coverage-out", default="")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    rows = [
        json.loads(line)
        for line in (data_root / "eval" / "acceptance" / "dataset.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    stop = None if args.limit is None else args.offset + args.limit
    svc = build_service(data_root=data_root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    with out.open("w", encoding="utf-8") as handle:
        for row in rows[args.offset : stop]:
            answer = answer_with_slots(row["question"], svc.retriever, top_k=args.top_k)
            cites = [
                {"doc_id": str(citation.doc_id), "section": str(citation.section)}
                for citation in answer.citations
            ]
            record = AuditRecord(
                id=row["id"],
                source="acceptance",
                question=row["question"],
                visible_answer=answer.text,
                citations=cites,
                evidence_ids=sorted({item["doc_id"] for item in cites}),
                abstained=bool(answer.abstained),
                reason=str(answer.reason),
                pipeline_stage="abstain" if answer.abstained else "compose",
                reference=row.get("reference_answer", ""),
                theme=_theme(row["question"]),
                gap_status="gap" if answer.abstained else "covered",
                trace_ref="slot-arm",
                answer_kind="delivery",
            )
            payload = record.to_dict()
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            written.append(payload)
            if len(written) % 25 == 0:
                print(f"generated {len(written)}", flush=True)
    print(f"wrote {len(written)} records -> {out}", flush=True)
    if args.coverage_out:
        coverage = _coverage(rows[args.offset : stop], written)
        Path(args.coverage_out).write_text(
            json.dumps(coverage, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(json.dumps({k: v for k, v in coverage.items() if k != "per_question"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
