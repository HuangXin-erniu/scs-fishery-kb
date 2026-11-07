from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .points import ConceptSource, PointOverrides
from .scoring import ScoringConfig, score_row


def _citation_payload(citations: Any) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in citations or []:
        if hasattr(item, "model_dump"):
            payload.append(item.model_dump())
        elif isinstance(item, dict):
            payload.append(item)
        else:
            payload.append({"doc_id": getattr(item, "doc_id", ""), "section": ""})
    return payload


def query_service(service: Any, question: str, *, llm_fn: Callable[..., Any] | None = None) -> dict:
    """Run one question through the service (or the optional LLM arm)."""
    started = time.perf_counter()
    if llm_fn is None:
        result = service.query(question, web="off")
        return {
            "answer": str(getattr(result, "answer", "")),
            "citations": _citation_payload(getattr(result, "citations", [])),
            "abstained": bool(getattr(result, "abstained", False)),
            "reason": str(getattr(result, "reason", "")),
            "mode": str(getattr(result, "mode", "")),
            "latency_ms": int(getattr(result, "latency_ms", 0) or 0),
        }
    retriever = getattr(service, "retriever", None)
    hits = retriever.search(question, top_k=5) if retriever is not None else []
    answer = llm_fn(question, hits)
    return {
        "answer": str(getattr(answer, "text", "")),
        "citations": _citation_payload(getattr(answer, "citations", [])),
        "abstained": bool(getattr(answer, "abstained", False)),
        "reason": str(getattr(answer, "reason", "")),
        "mode": "llm",
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def run_acceptance(
    rows: list[dict[str, Any]],
    service: Any,
    *,
    docmap: Any,
    concepts: ConceptSource,
    overrides: PointOverrides,
    config: ScoringConfig,
    llm_fn: Callable[..., Any] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> list[dict[str, Any]]:
    """Score every selected row; a per-question failure is recorded, never hidden."""
    scored: list[dict[str, Any]] = []
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        try:
            result = query_service(service, str(row.get("question") or ""), llm_fn=llm_fn)
            error = ""
        except Exception as exc:  # noqa: BLE001 - a failing question is data
            result = {
                "answer": "",
                "citations": [],
                "abstained": True,
                "reason": "runner_error",
                "mode": "error",
                "latency_ms": 0,
            }
            error = f"{type(exc).__name__}: {exc}"
        scored_row = score_row(
            row,
            result,
            docmap=docmap,
            concepts=concepts,
            overrides=overrides,
            config=config,
        )
        scored_row["question"] = row.get("question")
        scored_row["error"] = error
        scored.append(scored_row)
        if progress is not None and (index % 50 == 0 or index == total):
            progress(index, total)
    return scored
