#!/usr/bin/env python3
"""Short-answer arm on the public regression set.

Runs the optional short arm over every public item and reports how often it
actually produces a short answer, how long that answer is, whether its citations
resolve, recall@5 among answered retrieval rows and how the no-evidence rows are
handled. Report-only: the private acceptance instrument is never read.

The short arm validates each claim against its evidence window, so a run with
``SCS_FKB_VERIFY_ANSWERS=on`` is the production-shaped one; without the flag the
no-evidence rows are answered instead of refused.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.service_v2.answer import build_service

REFUSAL_RE = re.compile(r"证据不足|无法回答|没有找到|无相关证据|不能确定|缺乏依据")
CHANNEL_RE = re.compile(r"渠道[:：]")
SHORT_REASON = "short_compose"


def _load_set(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"empty public set: {path}")
    return entries


def _hit(result, row: dict) -> bool:
    cited = {item.doc_id for item in result.citations}
    if not cited:
        return False
    expected = set(row.get("expected_docs") or [])
    prefix = str(row.get("expected_prefix") or "")
    if cited & expected:
        return True
    return bool(prefix) and any(doc.startswith(prefix) for doc in cited)


def _rate(items: list[dict], key: str) -> float | None:
    return round(sum(1 for item in items if item[key]) / len(items), 4) if items else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--set", default=str(REPO_ROOT / "configs" / "eval-public.yaml"))
    parser.add_argument("--task-id", default="P19-ANS-215")
    parser.add_argument(
        "--hits",
        type=int,
        default=8,
        help="evidence hits the short arm may use (llm_answer.MAX_HITS)",
    )
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2

    os.environ.setdefault("SCS_FKB_WEB", "off")
    from scs_fkb.answer_v3 import llm_answer, short_arm

    llm_answer.MAX_HITS = args.hits
    short_arm.MAX_HITS = args.hits
    entries = _load_set(Path(args.set))
    service = build_service(data_root=args.data_root)
    registry = getattr(service, "_registry", {})

    rows: list[dict] = []
    for entry in entries:
        started = time.perf_counter()
        result = service.query(str(entry["question"]), web="off", short=True)
        elapsed = int((time.perf_counter() - started) * 1000)
        text = result.answer or ""
        cited = {item.doc_id for item in result.citations}
        rows.append(
            {
                "id": entry["id"],
                "type": entry["type"],
                "short": result.reason == SHORT_REASON,
                "abstained": bool(result.abstained),
                "reason": result.reason,
                "chars": len(text),
                "within_cap": len(text) <= 300,
                "citations": len(cited),
                "citation_resolved": bool(cited) and all(doc in registry for doc in cited),
                "recall_hit": _hit(result, entry) if entry["type"] != "abstain" else None,
                "refusal_text": bool(REFUSAL_RE.search(text)),
                "channel": bool(CHANNEL_RE.search(text)),
                "latency_ms": elapsed,
            }
        )

    retrieval = [item for item in rows if item["type"] != "abstain"]
    answered = [item for item in rows if not item["abstained"]]
    answered_retrieval = [item for item in answered if item["type"] != "abstain"]
    abstain = [item for item in rows if item["type"] == "abstain"]
    short = [item for item in rows if item["short"]]
    latencies = sorted(item["latency_ms"] for item in rows)

    metrics = {
        "rows": len(rows),
        "retrieval_rows": len(retrieval),
        "abstain_rows": len(abstain),
        "answered_rows": len(answered),
        "short_rows": len(short),
        "short_share": round(len(short) / len(rows), 4) if rows else None,
        "short_mean_chars": round(statistics.mean(item["chars"] for item in short), 1)
        if short
        else None,
        "short_within_cap": sum(1 for item in short if item["within_cap"]),
        "short_citation_resolution": _rate(short, "citation_resolved"),
        "recall_at_5": _rate(answered_retrieval, "recall_hit"),
        "citation_resolution": _rate(answered, "citation_resolved"),
        "within_cap": _rate(answered, "within_cap"),
        "abstain_flag_rate": _rate(abstain, "abstained"),
        "abstain_channel_rate": _rate(abstain, "channel"),
        "abstain_misanswer_rate": round(
            sum(1 for item in abstain if not item["abstained"] and not item["refusal_text"])
            / len(abstain),
            4,
        )
        if abstain
        else None,
        "median_ms": int(statistics.median(latencies)) if latencies else None,
        "p95_ms": latencies[int(len(latencies) * 0.95) - 1] if latencies else None,
        "reasons": dict(Counter(item["reason"] for item in rows)),
    }

    report = {
        "set": Path(args.set).name,
        "verifier": os.environ.get("SCS_FKB_VERIFY_ANSWERS", "off"),
        "evidence_hits": args.hits,
        "metrics": metrics,
        "rows": rows,
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.run_root:
        directory = Path(args.run_root).expanduser() / args.task_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "short-public.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [
            "# Short-answer arm on the public set",
            "",
            f"- Set: `{report['set']}` ({metrics['rows']} rows: {metrics['retrieval_rows']} "
            f"retrieval, {metrics['abstain_rows']} no-evidence)",
            f"- Sufficiency verifier: `{report['verifier']}`; evidence hits per answer: "
            f"{report['evidence_hits']}",
            f"- Valid short answers: {metrics['short_rows']}/{metrics['rows']} "
            f"({metrics['short_share']}); mean {metrics['short_mean_chars']} characters, "
            f"{metrics['short_within_cap']} within the cap",
            f"- Recall@5 among answered retrieval rows: {metrics['recall_at_5']}",
            f"- Citation resolution among answered rows: {metrics['citation_resolution']}",
            f"- Abstain flag / channel / misanswer on no-evidence rows: "
            f"{metrics['abstain_flag_rate']} / {metrics['abstain_channel_rate']} / "
            f"{metrics['abstain_misanswer_rate']}",
            f"- Latency: median {metrics['median_ms']} ms, P95 {metrics['p95_ms']} ms",
            "",
            "Fallback reasons: "
            + ", ".join(f"`{key}` {value}" for key, value in metrics["reasons"].items()),
        ]
        (directory / "short-public.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"report: {directory / 'short-public.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
