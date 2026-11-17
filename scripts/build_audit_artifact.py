#!/usr/bin/env python3
"""Build the canonical audit artifact (visible answers only).

The audit consumes this file, never the 100 KB dump blocks.  For already
delivered blind/recheck answers use ``--mode reviewed``; for the legacy 512 dump
use ``--mode dump-trimmed`` which only keeps the delivery-style body before the
diagnostic sections.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.audit.normalize import citations  # noqa: E402
from scs_fkb.audit.schema import AuditRecord, write_jsonl  # noqa: E402

THEME_TERMS = {
    "休渔": ("休渔", "禁渔", "伏季"),
    "证照": ("许可证", "船网工具", "登记", "过户", "证书"),
    "执法": ("处罚", "罚款", "执法", "没收", "立案"),
    "生态": ("保护区", "珊瑚", "海草", "红树林", "生态", "玳瑁", "海龟", "鲎"),
    "预报": ("预报", "渔情", "台风", "厄尔尼诺", "海温", "赤潮"),
    "补贴": ("补贴", "补助", "减船", "油价"),
}


def _theme(question: str, fallback: str = "其他") -> str:
    for name, terms in THEME_TERMS.items():
        if any(term in question for term in terms):
            return name
    return fallback


def _stage(reason: str, abstained: bool) -> str:
    if abstained:
        return "abstain"
    if "fallback" in reason or "plain" in reason:
        return "fallback"
    if reason in {"ok", "dump_compose", "standard", "delivery"}:
        return "compose"
    return "postprocess"


def _parse_citations(text: str) -> list[dict[str, str]]:
    return [{"doc_id": doc, "section": section.strip()} for doc, section in citations(text or "")]


def _evidence_ids(text: str) -> list[str]:
    return sorted({doc for doc, _section in citations(text or "")})


def _reviewed(
    run_root: Path, dataset: dict[str, dict[str, Any]], use: list[str]
) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    for name in use:
        path = run_root / "FINAL-ACCEPT" / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            meta = dataset.get(row["id"], {})
            answer = row.get("answer", "")
            records.append(
                AuditRecord(
                    id=row["id"],
                    source=row.get("source", "reviewed"),
                    question=row.get("question", meta.get("question", "")),
                    visible_answer=answer,
                    citations=_parse_citations(answer) or _parse_citations(row.get("evidence", "")),
                    evidence_ids=_evidence_ids(row.get("evidence", "")),
                    abstained=bool(row.get("abstained", False)),
                    reason=str(row.get("reason", "delivery")),
                    pipeline_stage=_stage(
                        str(row.get("reason", "delivery")), bool(row.get("abstained", False))
                    ),
                    reference=row.get("reference", meta.get("reference_answer", "")),
                    theme=_theme(row.get("question", meta.get("question", ""))),
                    trace_ref=f"FINAL-ACCEPT/{name}",
                    answer_kind="delivery",
                )
            )
    return records


def _trim_dump(answer: str) -> str:
    for marker in ("\n依据摘录：", "\n数值对照："):
        if marker in answer:
            answer = answer.split(marker, 1)[0]
    return answer.strip()


def _dump(
    run_root: Path, dataset: dict[str, dict[str, Any]], limit: int | None
) -> list[AuditRecord]:
    path = run_root / "FINAL-ACCEPT" / "answers-dump-final.jsonl"
    records: list[AuditRecord] = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if limit and index >= limit:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            meta = dataset.get(row["id"], {})
            answer = _trim_dump(str(row.get("answer", "")))
            records.append(
                AuditRecord(
                    id=row["id"],
                    source="acceptance",
                    question=row.get("question", meta.get("question", "")),
                    visible_answer=answer,
                    citations=_parse_citations(answer),
                    evidence_ids=[],
                    abstained=bool(row.get("abstained", False)),
                    reason=str(row.get("reason", "")),
                    pipeline_stage=_stage(
                        str(row.get("reason", "")), bool(row.get("abstained", False))
                    ),
                    reference=meta.get("reference_answer", ""),
                    theme=_theme(row.get("question", meta.get("question", ""))),
                    trace_ref="FINAL-ACCEPT/answers-dump-final.jsonl",
                    answer_kind="dump_trimmed",
                )
            )
    return records


def _service_512(
    run_root: Path,
    data_root: Path,
    dataset: dict[str, dict[str, Any]],
    limit: int | None,
    answer_mode: str,
    timeout: int = 90,
    offset: int = 0,
) -> list[AuditRecord]:
    from scs_fkb.service_v2.answer import build_service

    svc = build_service(data_root=data_root)
    records: list[AuditRecord] = []
    path = data_root / "eval" / "acceptance" / "dataset.jsonl"
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    stop = None if limit is None else offset + limit
    for row in rows[offset:stop]:

        def _alarm(*_args: object) -> None:
            raise TimeoutError

        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(timeout)
        try:
            response = svc.query(row["question"], web="off", mode=answer_mode)
        except TimeoutError:
            print(f"timeout {row['id']}", flush=True)
            signal.alarm(0)
            continue
        except Exception as exc:  # noqa: BLE001 - audit must keep going
            print(f"error {row['id']}: {type(exc).__name__}", flush=True)
            signal.alarm(0)
            continue
        finally:
            signal.alarm(0)
        cites = [
            {"doc_id": str(c.doc_id), "section": str(getattr(c, "section", ""))}
            for c in (response.citations or [])
        ]
        records.append(
            AuditRecord(
                id=row["id"],
                source="acceptance",
                question=row["question"],
                visible_answer=response.answer,
                citations=cites,
                evidence_ids=sorted({c["doc_id"] for c in cites}),
                abstained=bool(response.abstained),
                reason=str(response.reason),
                pipeline_stage=_stage(str(response.reason), bool(response.abstained)),
                reference=row.get("reference_answer", ""),
                theme=_theme(row["question"]),
                gap_status=str(getattr(response, "answerability", "")),
                trace_ref=f"service:{answer_mode}",
                answer_kind="delivery",
            )
        )
        if len(records) % 25 == 0:
            print(f"generated {len(records)}", flush=True)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["reviewed", "dump-trimmed", "service"], default="reviewed"
    )
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT", "runs"))
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--answer-mode", default="standard")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--reviewed", nargs="*", default=["final-blind-30.jsonl", "final-recheck2-20.jsonl"]
    )
    args = parser.parse_args(argv)
    dataset = {}
    dataset_path = Path(args.data_root) / "eval" / "acceptance" / "dataset.jsonl"
    if dataset_path.exists():
        for line in dataset_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                dataset[row["id"]] = row
    run_root = Path(args.run_root)
    if args.mode == "reviewed":
        records = _reviewed(run_root, dataset, args.reviewed)
    elif args.mode == "service":
        records = _service_512(
            run_root, Path(args.data_root), dataset, args.limit, args.answer_mode
        )
    else:
        records = _dump(run_root, dataset, args.limit)
    write_jsonl(Path(args.out), records)
    print(f"wrote {len(records)} audit records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
