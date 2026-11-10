#!/usr/bin/env python3
"""RAGAS-compatible judge for the public set: faithfulness, relevancy, precision/recall.

The metric definitions follow RAGAS; the judge is the project's OpenAI-compatible
client with temperature 0 and a local cache. This is a report, not a merge gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.llm import LLMClient, LLMConfig, LLMError, parse_json_object
from scs_fkb.rag import LLMCache
from scs_fkb.service_v2.answer import AnswerService, build_service

PROMPT_VERSION = "ragas-judge-v1"
MAX_ANSWER = 1200
MAX_CONTEXT = 500

FAITHFULNESS = (
    "判断答案中的事实是否能被证据支持。逐句检查；只统计有事实主张的句子。"
    '输出 JSON：{"score": 0到1的小数, "unsupported": ["…"]}。'
)
RELEVANCY = (
    '判断答案是否直接回答了问题（不评价对错，只看相关与完整）。输出 JSON：{"score": 0到1的小数}。'
)
PRECISION = (
    "给定参考答案和检索证据，判断证据中有多少是回答该问题真正需要的。"
    '输出 JSON：{"score": 0到1的小数}。'
)
RECALL = (
    "给定参考答案和检索证据，判断参考答案的要点有多少能在证据中找到。"
    '输出 JSON：{"score": 0到1的小数}。'
)


def _key(kind: str, question: str, answer: str, contexts: str, model: str) -> str:
    digest = hashlib.sha256(
        f"{PROMPT_VERSION}\n{kind}\n{question}\n{answer}\n{contexts}\n{model}".encode()
    ).hexdigest()
    return f"judge-{digest[:24]}.json"


def _judge(
    client: LLMClient,
    cache: LLMCache,
    kind: str,
    system: str,
    question: str,
    answer: str,
    contexts: str,
) -> float | None:
    key = _key(kind, question, answer, contexts, client.config.model)
    cached = cache.get(key)
    if cached is not None:
        value = cached
    else:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"问题：\n{question}\n\n答案：\n{answer[:MAX_ANSWER]}\n\n"
                    f"证据：\n{contexts}\n\n按 JSON 输出。"
                ),
            },
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=500))
        except LLMError:
            return None
        cache.put(key, value)
    try:
        score = float(value.get("score"))
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, score))


def _contexts(service: AnswerService, result: Any) -> str:
    retriever = service.retriever
    chunks = getattr(retriever, "chunks", []) or []
    parts: list[str] = []
    for citation in result.citations[:5]:
        match = next(
            (
                chunk
                for chunk in chunks
                if chunk.doc_id == citation.doc_id
                and (not citation.section or chunk.section.startswith(citation.section))
            ),
            None,
        )
        text = " ".join((match.text if match else citation.snippet).split())[:MAX_CONTEXT]
        parts.append(f"[{citation.doc_id} §{citation.section or ''}] {text}")
    if not parts:
        parts = [f"[{citation.doc_id}] {citation.snippet}" for citation in result.citations[:5]]
    return "\n\n".join(parts)


def _rows(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [row for row in data.get("entries") or [] if row.get("type") != "abstain"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--set", default=str(REPO_ROOT / "configs" / "eval-public.yaml"))
    parser.add_argument("--task-id", default="P18-ANS-212")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sample", type=int, default=0, help="balanced sample incl. references")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    rows = _rows(Path(args.set))
    if args.limit:
        rows = rows[: args.limit]
    if args.sample:
        references = [row for row in rows if row.get("reference_answer")]
        plain = [row for row in rows if not row.get("reference_answer")]
        keep_refs = references[: max(1, min(4, args.sample // 3))]
        keep_plain = plain[: max(1, args.sample - len(keep_refs))]
        rows = keep_plain + keep_refs
    config = LLMConfig.from_env()
    client = LLMClient(config)
    cache = LLMCache(Path(args.data_root) / "llm-cache")
    dump = build_service(data_root=args.data_root)
    dump._llm = None  # deterministic dump, no rewrite
    short = build_service(data_root=args.data_root)
    short.answer_mode = "short"

    metrics: dict[str, dict[str, float | int]] = {}
    for arm, service in (("dump", dump), ("short", short)):
        started = time.perf_counter()
        faith: list[float] = []
        relev: list[float] = []
        precision: list[float] = []
        recall: list[float] = []
        for row in rows:
            result = service.query(str(row["question"]), web="off", short=(arm == "short"))
            contexts = _contexts(service, result)
            answer = result.answer
            f = _judge(
                client, cache, "faithfulness", FAITHFULNESS, row["question"], answer, contexts
            )
            r = _judge(client, cache, "relevancy", RELEVANCY, row["question"], answer, contexts)
            if f is not None:
                faith.append(f)
            if r is not None:
                relev.append(r)
            reference = str(row.get("reference_answer") or "")
            if reference:
                p = _judge(
                    client, cache, "precision", PRECISION, row["question"], reference, contexts
                )
                q = _judge(client, cache, "recall", RECALL, row["question"], reference, contexts)
                if p is not None:
                    precision.append(p)
                if q is not None:
                    recall.append(q)
        metrics[arm] = {
            "rows": len(rows),
            "faithfulness": round(sum(faith) / len(faith), 4) if faith else 0.0,
            "answer_relevancy": round(sum(relev) / len(relev), 4) if relev else 0.0,
            "context_precision": round(sum(precision) / len(precision), 4) if precision else None,
            "context_recall": round(sum(recall) / len(recall), 4) if recall else None,
            "seconds": round(time.perf_counter() - started, 1),
        }

    report = {
        "set": Path(args.set).name,
        "rows": len(rows),
        "model": config.model,
        "metrics": metrics,
        "note": "RAGAS-compatible report; not a merge gate.",
    }
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else json.dumps(report, ensure_ascii=False, indent=2)
    )
    if args.run_root:
        directory = Path(args.run_root).expanduser() / args.task_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "ragas.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lines = [
            "# RAGAS-compatible judge",
            "",
            f"- Set: {report['set']} ({report['rows']} rows)",
            f"- Judge model: `{report['model']}`",
            "",
            "| Arm | Faithfulness | Answer relevancy | Context precision | "
            "Context recall | Seconds |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for arm, row in metrics.items():
            lines.append(
                f"| {arm} | {row['faithfulness']} | {row['answer_relevancy']} | "
                f"{row['context_precision']} | {row['context_recall']} | {row['seconds']} |"
            )
        lines.append("")
        lines.append(report["note"])
        (directory / "ragas.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"report: {directory / 'ragas.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
