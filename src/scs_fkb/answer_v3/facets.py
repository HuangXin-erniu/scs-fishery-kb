"""Answer one facet at a time with citation and number checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from ..llm import LLMClient, LLMError, parse_json_object
from ..rag import LLMCache
from .decompose import Facet
from .llm_answer import (
    _citations_from_text,
    _evidence,
    _number_problems,
    _resolve_citations,
    _sentence_problems,
)

PROMPT_VERSION = "facet-answer-v1"
MAX_EVIDENCE_CHARS = 3500

SYSTEM = (
    "你回答一个渔业子问题。只使用给出的证据，用一到两句话直接回答，不要铺垫。\n"
    "每个事实句都必须带引用，格式 [DOC_ID §章节] 或 [DOC_ID p.页码]，DOC_ID、章节、页码"
    "必须与证据清单一致。数字必须逐字来自证据并带单位。证据只覆盖子问题的一部分时，先回答"
    "已覆盖部分并在句末写“（缺口：……）”；只有完全找不到相关条款时才 abstained 置 true。\n"
    '只输出 JSON：{"abstained": false, "answer": "……", "reason": "ok"}'
)


@dataclass(frozen=True)
class FacetAnswer:
    facet: Facet
    text: str
    citations: tuple[Any, ...]
    hits: tuple[Any, ...]
    abstained: bool = False
    reason: str = ""


def _key(facet: str, context: str, model: str) -> str:
    digest = hashlib.sha256(f"{PROMPT_VERSION}\n{facet}\n{context}\n{model}".encode()).hexdigest()
    return f"facet-ans-{digest[:24]}.json"


def answer_facet(
    facet: Facet,
    hits: list[Any],
    client: LLMClient,
    cache: LLMCache | None,
) -> FacetAnswer:
    """Answer one facet; abstain when the cited evidence cannot support it."""
    if not hits:
        return FacetAnswer(facet, "", (), (), True, "no_evidence")
    hits = _enrich(hits)
    context, by_label = _evidence(hits)
    if not context:
        return FacetAnswer(facet, "", (), (), True, "no_evidence")
    key = _key(facet.text, context, client.config.model)
    value = cache.get(key) if cache is not None else None
    if value is None:
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"子问题：{facet.text}\n\n证据：\n{context}\n\n按 JSON 输出。",
            },
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=1200))
        except LLMError:
            return FacetAnswer(facet, "", (), (), True, "model_error")
        if cache is not None:
            cache.put(key, value)
    if value.get("abstained") is True:
        return FacetAnswer(
            facet, "", (), (), True, f"abstain:{value.get('reason') or ''}".rstrip(":")
        )
    text = str(value.get("answer") or "").strip()
    if not text:
        return FacetAnswer(facet, "", (), (), True, "empty")
    problems = _sentence_problems(text, by_label) + _number_problems(text, by_label)
    if problems:
        return FacetAnswer(
            facet, text, (), tuple(hits), True, f"invalid:{problems[0].split(':')[0]}"
        )
    valid, invalid = _resolve_citations(text, hits)
    if not valid:
        return FacetAnswer(facet, text, (), tuple(hits), True, "citation_invalid")
    citations = tuple(_citations_from_text(text, hits))
    if not citations:
        return FacetAnswer(facet, text, (), tuple(hits), True, "no_citation")
    return FacetAnswer(facet, text, citations, tuple(hits), False, "ok")


def _enrich(hits: list[Any]) -> list[Any]:
    from .llm_answer import _enrich as enrich

    return enrich(hits)


__all__ = ["FacetAnswer", "answer_facet", "PROMPT_VERSION"]
