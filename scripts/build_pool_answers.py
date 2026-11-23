#!/usr/bin/env python3
"""Build visible-answer JSONL for a frozen pool CSV through the product path.

The 512 instrument has its own builder (``build_audit_artifact.py``); this
script is the equivalent for the smaller acceptance pools (pool-v3..v6) whose
question files are CSV with ``id,question`` columns.  It resumes by skipping ids
already present in ``--out`` and never rewrites an existing answer.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, help="CSV with id,question columns")
    parser.add_argument("--out", required=True, help="JSONL to append to (resumable)")
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--answer-mode", default="standard")
    return parser.parse_args(argv)


def _existing(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        str(json.loads(line)["id"])
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    questions = Path(args.questions)
    out = Path(args.out)
    rows = [row for row in csv.DictReader(questions.open(encoding="utf-8-sig")) if row.get("id")]
    done = _existing(out)
    from scs_fkb.service_v2.answer import build_service

    service = build_service(data_root=Path(args.data_root))
    generated = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        for row in rows[args.offset :]:
            if args.limit and generated >= args.limit:
                break
            question_id = str(row["id"]).strip()
            if question_id in done:
                continue

            def _alarm(*_args: object) -> None:
                raise TimeoutError

            signal.signal(signal.SIGALRM, _alarm)
            signal.alarm(args.timeout)
            try:
                response = service.query(row["question"], web="off", mode=args.answer_mode)
            except TimeoutError:
                print(f"timeout {question_id}", flush=True)
                continue
            except Exception as exc:  # noqa: BLE001 - keep the batch moving
                print(f"error {question_id}: {type(exc).__name__}", flush=True)
                continue
            finally:
                signal.alarm(0)
            citations = [
                {"doc_id": str(cite.doc_id), "section": str(getattr(cite, "section", ""))}
                for cite in (response.citations or [])
            ]
            record = {
                "id": question_id,
                "source": questions.stem,
                "question": row["question"],
                "visible_answer": response.answer,
                "citations": citations,
                "abstained": bool(response.abstained),
                "reason": str(response.reason),
                "answerability": str(getattr(response, "answerability", "")),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            generated += 1
            if generated % 10 == 0:
                print(f"generated {generated}", flush=True)
    print(f"done generated={generated} total={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
