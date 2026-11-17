#!/usr/bin/env python3
"""Generate the 512 visible-answer audit artifact with one-question hard timeouts.

A persistent worker loads the service once.  Each request is guarded by a
readline timeout; if the worker is blocked in an LLM/SSL call it is killed and
restarted.  Timed-out questions are recorded as ``service_timeout`` and never
count as passes.  ``--resume`` keeps completed ids and appends new records.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scs_fkb.audit.schema import AuditRecord  # noqa: E402

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
        env = dict(os.environ)
        env.setdefault("SCS_FKB_WEB", "off")
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
            env=env,
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


def _done_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    done: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            done.add(str(json.loads(line).get("id", "")))
        except json.JSONDecodeError:
            continue
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--answer-mode", default="standard")
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--start-timeout", type=float, default=180.0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--questions", default="", help="JSONL with id/question fields")
    parser.add_argument("--ids", default="", help="comma-separated ids to run")
    parser.add_argument("--source", default="acceptance")
    parser.add_argument(
        "--trace",
        default="",
        help="LLM call trace JSONL; defaults to <out>.llm-trace.jsonl",
    )
    args = parser.parse_args(argv)
    out_path = Path(args.out)
    trace_path = Path(args.trace) if args.trace else out_path.with_suffix(".llm-trace.jsonl")
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["SCS_FKB_LLM_TRACE"] = str(trace_path)
    data_root = Path(args.data_root)
    questions_path = (
        Path(args.questions)
        if args.questions
        else data_root / "eval" / "acceptance" / "dataset.jsonl"
    )
    rows = [
        json.loads(line)
        for line in questions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.ids:
        wanted = {part.strip() for part in args.ids.split(",") if part.strip()}
        rows = [row for row in rows if str(row["id"]) in wanted]
    stop = None if args.limit is None else args.offset + args.limit
    rows = rows[args.offset : stop]
    done = _done_ids(out_path) if args.resume else set()
    if args.resume and done:
        rows = [row for row in rows if str(row["id"]) not in done]
        print(f"resume: {len(done)} records already done; {len(rows)} remaining", flush=True)
    worker = Worker(data_root, args.answer_mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    timeouts = 0
    with out_path.open("a", encoding="utf-8") as handle:
        try:
            for index, row in enumerate(rows):
                started = time.perf_counter()
                response = worker.ask(
                    row["id"],
                    row["question"],
                    args.start_timeout if index == 0 and not done else args.timeout,
                )
                wall_ms = int((time.perf_counter() - started) * 1000)
                if not response.get("ok"):
                    timeouts += 1
                    record = AuditRecord(
                        id=row["id"],
                        source=str(row.get("source") or args.source),
                        question=row["question"],
                        visible_answer="审计超时或服务错误，未生成交付答案。",
                        abstained=True,
                        reason=f"service_{response.get('error', 'error')}",
                        pipeline_stage="abstain",
                        reference=row.get("reference_answer", ""),
                        theme=theme(row["question"]),
                        answer_kind="service_timeout",
                        trace_ref=trace_path.name,
                        metadata={
                            "wall_ms": wall_ms,
                            "answer_mode": args.answer_mode,
                            "timeout_seconds": args.timeout,
                        },
                    )
                    print(f"{row['id']} {response.get('error')} ({wall_ms}ms)", flush=True)
                else:
                    cites = list(response.get("citations") or [])
                    seen_cites = {
                        (str(item.get("doc_id", "")), str(item.get("section", "")))
                        for item in cites
                    }
                    for doc_id, section in re.findall(
                        r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]", response.get("answer", "")
                    ):
                        key = (doc_id, section.strip())
                        if key not in seen_cites:
                            seen_cites.add(key)
                            cites.append({"doc_id": doc_id, "section": section.strip()})
                    record = AuditRecord(
                        id=row["id"],
                        source=str(row.get("source") or args.source),
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
                        trace_ref=trace_path.name,
                        answer_kind="delivery",
                        metadata={
                            "wall_ms": wall_ms,
                            "worker_elapsed_ms": int(response.get("elapsed_ms") or 0),
                            "answer_mode": args.answer_mode,
                        },
                    )
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                handle.flush()
                written += 1
                if written % 10 == 0:
                    print(f"done {written} (timeouts={timeouts})", flush=True)
        finally:
            worker.stop()
    total = len(_done_ids(out_path))
    print(f"appended {written} records; total={total}; timeouts={timeouts} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
