#!/usr/bin/env python3
"""Generate the 512 visible-answer audit artifact with one-question hard timeouts.

A persistent worker loads the service once.  Each request is guarded by a
readline timeout; if the worker is blocked in an LLM/SSL call it is killed and
restarted.  Timed-out questions are recorded as ``service_timeout`` and never
count as passes.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scs_fkb.audit.schema import AuditRecord, write_jsonl  # noqa: E402

THEMES = {
    "休渔": ("休渔", "禁渔", "伏季"),
    "证照": ("许可证", "船网工具", "登记", "过户", "证书"),
    "执法": ("处罚", "罚款", "执法", "没收", "立案"),
    "生态": ("保护区", "珊瑚", "海草", "红树林", "生态", "玳瑁", "海龟", "鲎"),
    "预报": ("预报", "渔情", "台风", "厄尔尼诺", "海温", "赤潮"),
    "补贴": ("补贴", "补助", "减船", "油价"),
}


def theme(question: str) -> str:
    for name, terms in THEMES.items():
        if any(term in question for term in terms):
            return name
    return "其他"


def stage(reason: str, abstained: bool) -> str:
    if abstained:
        return "abstain"
    if "fallback" in reason or "plain" in reason:
        return "fallback"
    if reason in {"ok", "standard", "dump_compose"}:
        return "compose"
    return "postprocess"


class Worker:
    def __init__(self, data_root: Path, answer_mode: str) -> None:
        self.data_root = data_root
        self.answer_mode = answer_mode
        self.proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_service_worker.py"),
                "--data-root",
                str(self.data_root),
                "--answer-mode",
                self.answer_mode,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def stop(self) -> None:
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait(timeout=10)
            self.proc = None

    def ask(self, record_id: str, question: str, timeout: float) -> dict:
        if self.proc is None or self.proc.poll() is not None:
            self.stop()
            self.start()
        assert (
            self.proc is not None and self.proc.stdin is not None and self.proc.stdout is not None
        )
        self.proc.stdin.write(
            json.dumps({"id": record_id, "question": question}, ensure_ascii=False) + "\n"
        )
        self.proc.stdin.flush()
        ready, _w, _x = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            self.stop()
            return {"ok": False, "id": record_id, "error": "timeout"}
        line = self.proc.stdout.readline()
        if not line:
            self.stop()
            return {"ok": False, "id": record_id, "error": "worker_exit"}
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            self.stop()
            return {"ok": False, "id": record_id, "error": "bad_json"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--answer-mode", default="standard")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--start-timeout", type=float, default=120.0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    rows = [
        json.loads(line)
        for line in (data_root / "eval" / "acceptance" / "dataset.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    stop = None if args.limit is None else args.offset + args.limit
    rows = rows[args.offset : stop]
    worker = Worker(data_root, args.answer_mode)
    records: list[AuditRecord] = []
    try:
        for index, row in enumerate(rows):
            response = worker.ask(
                row["id"], row["question"], args.start_timeout if index == 0 else args.timeout
            )
            if not response.get("ok"):
                records.append(
                    AuditRecord(
                        id=row["id"],
                        source="acceptance",
                        question=row["question"],
                        visible_answer="审计超时或服务错误，未生成交付答案。",
                        abstained=True,
                        reason=f"service_{response.get('error', 'error')}",
                        pipeline_stage="abstain",
                        reference=row.get("reference_answer", ""),
                        theme=theme(row["question"]),
                        answer_kind="service_timeout",
                        trace_ref="service-worker",
                    )
                )
                print(f"{row['id']} {response.get('error')}", flush=True)
                continue
            cites = response.get("citations", [])
            records.append(
                AuditRecord(
                    id=row["id"],
                    source="acceptance",
                    question=row["question"],
                    visible_answer=response.get("answer", ""),
                    citations=cites,
                    evidence_ids=sorted({str(c.get("doc_id", "")) for c in cites}),
                    abstained=bool(response.get("abstained")),
                    reason=str(response.get("reason", "")),
                    pipeline_stage=stage(
                        str(response.get("reason", "")), bool(response.get("abstained"))
                    ),
                    reference=row.get("reference_answer", ""),
                    theme=theme(row["question"]),
                    gap_status=str(response.get("answerability", "")),
                    trace_ref="service-worker",
                    answer_kind="delivery",
                )
            )
            if len(records) % 10 == 0:
                print(f"done {len(records)}", flush=True)
    finally:
        worker.stop()
    write_jsonl(Path(args.out), records)
    timeouts = sum(1 for record in records if record.answer_kind == "service_timeout")
    print(f"wrote {len(records)} records; timeouts={timeouts} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
