#!/usr/bin/env python3
"""Persistent service worker for one-question-at-a-time audit generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--answer-mode", default="standard")
    args = parser.parse_args()
    from scs_fkb.service_v2.answer import build_service

    svc = build_service(data_root=Path(args.data_root))
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        os.environ["SCS_FKB_TRACE_ID"] = str(request.get("id", ""))
        started = time.perf_counter()
        try:
            response = svc.query(request["question"], web="off", mode=args.answer_mode)
            payload = {
                "ok": True,
                "id": request["id"],
                "answer": response.answer,
                "citations": [
                    {"doc_id": str(c.doc_id), "section": str(getattr(c, "section", ""))}
                    for c in (response.citations or [])
                ],
                "abstained": bool(response.abstained),
                "reason": str(response.reason),
                "answerability": str(getattr(response, "answerability", "")),
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }
        except Exception as exc:  # noqa: BLE001
            payload = {"ok": False, "id": request["id"], "error": type(exc).__name__}
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
