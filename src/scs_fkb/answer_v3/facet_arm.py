"""Facet arm: rewrite, decompose, answer facets, merge and verify."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..llm import LLMClient
from ..models import Answer, Citation
from ..rag import LLMCache
from ..retrieve_v2.rewrite import rewrite
from .decompose import Facet, decompose
from .facets import FacetAnswer, answer_facet
from .llm_answer import _evidence, _verify

MAX_FACETS = 5
FACET_TOP_K = 4


def _merge(question: str, answers: list[FacetAnswer], gaps: list[str]) -> str:
    core = next((item for item in answers if item.facet.kind == "core"), answers[0])
    lines = [f"结论：{core.text}"]
    rest = [item for item in answers if item is not core]
    for index, item in enumerate(rest, start=1):
        lines.append(f"{index}. {item.text}")
    if gaps:
        lines.append("缺口：" + "；".join(dict.fromkeys(gaps)))
    return "\n".join(lines)


def _citations(answers: list[FacetAnswer]) -> list[Citation]:
    seen: set[tuple[str, int, str]] = set()
    out: list[Citation] = []
    for item in answers:
        for citation in item.citations:
            key = (citation.doc_id, citation.page, citation.section)
            if key in seen:
                continue
            seen.add(key)
            out.append(citation)
    return out


def answer_with_facets(
    question: str,
    retriever: Any,
    client: LLMClient,
    cache: LLMCache | None = None,
    *,
    max_facets: int = MAX_FACETS,
    top_k: int = FACET_TOP_K,
    workers: int = 4,
    fallback: Callable[[], Answer] | None = None,
    base_answer: Answer | None = None,
    base_hits: list[Any] | None = None,
) -> Answer:
    """Decompose, answer each facet from its own clauses, merge and verify."""
    if base_answer is not None and base_answer.abstained:
        return base_answer
    rewrites = rewrite(question, client, cache)
    facets: list[Facet] = decompose(question, client, cache, max_facets=max_facets)
    prepared: list[tuple[Facet, list[Any]]] = []
    for facet in facets:
        hits = retriever.search_queries([facet.text, *rewrites], top_k=top_k)
        prepared.append((facet, hits))

    def work(item: tuple[Facet, list[Any]]) -> FacetAnswer:
        return answer_facet(item[0], item[1], client, cache)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(work, prepared))

    answered = [item for item in results if not item.abstained]
    if not answered:
        if fallback is not None:
            return fallback()
        return Answer(
            text="证据不足：拆分后的子问题都没有可支撑的条款，已按缺口处理。",
            citations=[],
            abstained=True,
            reason="no_facet_evidence",
        )
    gaps = [f"{item.facet.text}（{item.reason}）" for item in results if item.abstained]
    merged = _merge(question, answered, gaps)
    union_hits = [hit for item in answered for hit in item.hits]
    if base_hits:
        union_hits = list(base_hits) + union_hits
    if base_answer is not None and not base_answer.abstained and base_answer.text.strip():
        if base_answer.text.strip() not in merged:
            merged = f"{merged}\n综合：{base_answer.text.strip()}"
    _context, by_label = _evidence(union_hits)
    supported, reason = _verify(question, merged, by_label, client, cache)
    if not supported:
        if fallback is not None:
            return fallback()
        return Answer(
            text="证据不足：合并后的结论未被引用证据支持，已按缺口处理。",
            citations=[],
            abstained=True,
            reason=f"facet_unsupported:{reason}".rstrip(":"),
        )
    citations = _citations(answered)
    if base_answer is not None and not base_answer.abstained:
        seen = {(item.doc_id, item.page, item.section) for item in citations}
        for item in base_answer.citations:
            key = (item.doc_id, item.page, item.section)
            if key not in seen:
                seen.add(key)
                citations.append(item)
    return Answer(
        text=merged,
        citations=citations,
        abstained=False,
        reason="facet_compose",
    )


__all__ = ["MAX_FACETS", "answer_with_facets"]
