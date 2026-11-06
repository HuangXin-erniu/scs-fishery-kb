#!/usr/bin/env python3
"""Run 20 reviewed scenarios through the v2 answer service."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from pathlib import Path

SCENARIOS = [
    ("Q-E01", "南海区伏季休渔的起止日期与适用范围是什么？", "POL-CLOS-015"),
    ("Q-E02", "哪些作业类型在休渔期可以豁免或申请特许？", "POL-SPEC-041"),
    ("Q-E03", "海洋大中型渔船渔捞日志应记录哪些内容？", "POL-STD-010"),
    ("Q-E04", "捕捞日志漏填或错填会有什么管理后果？", "POL-STD-010"),
    ("Q-E09", "渔业捕捞许可证有效期内，作业场所或作业方式变更应如何办理？", "POL-STD-010"),
    (
        "Q-E10",
        "海洋捕捞准用渔具与过渡渔具最小网目尺寸制度从何时实施、适用哪些海区？",
        "POL-GEAR-016",
    ),
    ("Q-E12", "休渔期违规作业的处罚依据与处罚种类是什么？", "POL-LAW-009"),
    ("Q-E13", "渔业捕捞许可证年审需要符合哪些条件？", "POL-STD-010"),
    ("Q-E14", "制造、更新改造海洋捕捞渔船应遵守哪些船网工具指标规定？", "POL-STD-010"),
    ("Q-E15", "渔业船舶进出渔港应当遵守哪些报告和检查要求？", "POL-PORT-077"),
    ("Q-M01", "南海区伏季休渔制度的现行法律依据与修订沿革是什么？", "POL-LAW-009"),
    ("Q-M03", "渔捞日志的提交与上报要求是什么？", "POL-STD-010"),
    ("Q-M10", "申请海洋渔业捕捞许可证应当提交哪些资料？", "POL-STD-010"),
    ("Q-M12", "休渔期管理中的例外审批与处罚依据是什么？", "POL-LAW-009"),
    ("Q-M13", "渔业捕捞许可证在哪些情形下应换发或重新申请？", "POL-STD-010"),
    ("Q-M14", "渔具如何分类、命名和编号？", "OPS-STD-039"),
    ("Q-M15", "海洋捕捞信息采集抽样调查如何抽取样本渔船？", "OPS-STD-035"),
    ("Q-M16", "海洋渔业资源增殖保护费的年征收幅度是多少？", "POL-RULE-020"),
    ("Q-M17", "渔业船舶检验分为哪几种？", "POL-RULE-019"),
    ("Q-E07", "某渔场的历史渔汛期与主要经济鱼种是什么？", ""),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        raise SystemExit("set SCS_FKB_DATA_ROOT and SCS_FKB_RUN_ROOT")
    from scs_fkb.service_v2 import build_service

    service = build_service(data_root=args.data_root, run_root=args.run_root)
    rows = []
    for identifier, question, expected in SCENARIOS:
        result = service.query(question, web="off")
        cited_docs = {citation.doc_id for citation in result.citations}
        rows.append(
            {
                "id": identifier,
                "question": question,
                "expected": expected,
                "abstained": result.abstained,
                "reason": result.reason,
                "mode": result.mode,
                "citations": len(result.citations),
                "expected_cited": (not expected) or expected in cited_docs,
                "latency_ms": result.latency_ms,
                "answer": result.answer[:240].replace("\n", " "),
            }
        )
        print(
            f"{identifier:6s} abstained={result.abstained!s:5s} "
            f"cites={len(result.citations)} expected={rows[-1]['expected_cited']!s:5s} "
            f"{result.latency_ms:4d}ms {question}"
        )
    answered = [row for row in rows if not row["abstained"]]
    cited = [row for row in answered if row["citations"] > 0]
    expected_hit = [row for row in answered if row["expected_cited"]]
    report = Path(args.run_root).expanduser() / "P10-ANS-143" / "scenarios.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# P10-ANS-143 service scenarios",
        "",
        f"- Scenarios: {len(rows)}",
        f"- Answered: {len(answered)}",
        f"- Abstained: {len(rows) - len(answered)}",
        f"- Answers with citations: {len(cited)}",
        f"- Answers citing the expected document: {len(expected_hit)}",
        f"- Median latency: {statistics.median(row['latency_ms'] for row in rows):.0f} ms",
        "- Web used: 0 (network disabled for this report)",
        "",
        "| ID | Abstained | Mode | Cites | Expected doc cited | ms | Question |",
        "|---|---|---|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['abstained']} | {row['mode']} | {row['citations']} | "
            f"{row['expected_cited']} | {row['latency_ms']} | {row['question']} |"
        )
    lines += ["", "## Answer samples", ""]
    for row in rows[:8]:
        lines.append(f"- **{row['id']}** ({row['mode']}): {row['answer']}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"report": str(report), "answered": len(answered), "cited": len(cited)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
