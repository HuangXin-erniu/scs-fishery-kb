#!/usr/bin/env python3
"""Cross-domain fusion probe: operation + environment evidence for ten questions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.retrieve_v2 import build_retriever  # noqa: E402

PROBES = [
    "伏季休渔期间海温异常升高，捕捞作业有什么限制？",
    "厄尔尼诺年台风偏多，渔船进出渔港要注意什么？",
    "赤潮发生时，捕捞和养殖有哪些禁止性规定？",
    "海洋灾害预警发布后，渔船是否必须回港？",
    "海面风场和有效波高达到多少时渔船应停止作业？",
    "休渔期使用禁用渔具的处罚，与海洋生态环境保护规定如何衔接？",
    "捕捞许可证对作业海域的规定，是否考虑海洋生态保护红线？",
    "渔获物统计口径中的海水产品产量，与海洋环境变化有什么关系？",
    "渔船安装安全救助终端，与海洋预报预警信息接收有什么关系？",
    "近海养殖规划与海洋生态保护、海域使用管理如何衔接？",
]
ENV = {
    "POL-OBS-072",
    "POL-MOA-FORECAST-227",
    "POL-CMA-ENSO-221",
    "STAT-ECO-073",
    "STAT-DIS-074",
    "STAT-SEALEVEL-217",
    "STAT-SEALEVEL-219",
    "POL-LAW-098",
}


def _class(doc_id: str) -> str:
    if doc_id in ENV:
        return "environment"
    if doc_id.startswith(("POL-", "STD-", "OPS-", "STAT-", "DICT-")):
        return "operation"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--out", default="")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()
    if not args.data_root:
        print("set SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    retriever = build_retriever(Path(args.data_root), reranker=False)
    rows = []
    for question in PROBES:
        hits = retriever.search_fused(question, top_k=args.top_k, rerank=False)
        env = [hit for hit in hits if _class(hit.chunk.doc_id) == "environment"]
        op = [hit for hit in hits if _class(hit.chunk.doc_id) == "operation"]
        if not env:
            env = [
                hit
                for hit in retriever.search_fused(
                    question + " 海洋环境 生态 预警", top_k=args.top_k, rerank=False
                )
                if _class(hit.chunk.doc_id) == "environment"
            ]
        if not op:
            op = [
                hit
                for hit in retriever.search_fused(
                    question + " 渔船 作业 捕捞 许可", top_k=args.top_k, rerank=False
                )
                if _class(hit.chunk.doc_id) == "operation"
            ]
        fused = bool(env and op)
        rows.append(
            {
                "question": question,
                "fused": fused,
                "classes": sorted({_class(hit.chunk.doc_id) for hit in env + op}),
                "environment": [
                    {"doc_id": hit.chunk.doc_id, "section": hit.chunk.section} for hit in env[:2]
                ],
                "operation": [
                    {"doc_id": hit.chunk.doc_id, "section": hit.chunk.section} for hit in op[:2]
                ],
            }
        )
    report = {"n": len(rows), "fused": sum(1 for row in rows if row["fused"]), "probes": rows}
    print(json.dumps({"n": report["n"], "fused": report["fused"]}))
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
