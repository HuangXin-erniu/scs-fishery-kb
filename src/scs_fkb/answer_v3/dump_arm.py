"""Deterministic clause-dump arm: sentence-level quotations with citations."""

from __future__ import annotations

import os
import re
from typing import Any

from ..models import Answer
from ..rag import _citations_from_text
from .llm_answer import _enrich

MAX_HITS = int(os.environ.get("SCS_FKB_DUMP_HITS", "30"))
MAX_ANSWER_CHARS = int(os.environ.get("SCS_FKB_DUMP_CHARS", "9000"))
MIN_SENTENCE = 8
SENTENCE_RE = re.compile(r"(?<=[。；！？])")


def _label(chunk: Any) -> str:
    section = f" §{chunk.section}" if chunk.section else f" p.{chunk.page}"
    return f"[{chunk.doc_id}{section}]"


def _overlap(sentence: str, question: str) -> int:
    tokens = {token for token in re.findall(r"[\u4e00-\u9fa5]{2,4}", question)}
    return sum(1 for token in tokens if token in sentence)


def answer_with_dump(
    question: str,
    retriever: Any,
    *,
    queries: list[str] | None = None,
    max_hits: int = MAX_HITS,
    max_chars: int = MAX_ANSWER_CHARS,
) -> Answer:
    """Quote the retrieved clauses sentence by sentence; no model call."""
    hits = retriever.search_queries([question, *(queries or [])], top_k=max_hits)
    if not hits:
        return Answer(text="", citations=(), abstained=True, reason="no_evidence")
    hits = _enrich(hits)
    scored: list[tuple[int, str, Any]] = []
    for hit in hits:
        for sentence in SENTENCE_RE.split(hit.chunk.text):
            sentence = " ".join(sentence.split())
            if len(sentence) < MIN_SENTENCE:
                continue
            scored.append((_overlap(sentence, question), sentence, hit))
    if not scored:
        return Answer(text="", citations=(), abstained=True, reason="no_sentences")
    scored.sort(key=lambda item: (-item[0], item[1]))
    lines: list[str] = []
    used = 0
    first: str | None = None
    for _score, sentence, hit in scored:
        block = f"{sentence} {_label(hit.chunk)}"
        if used + len(block) > max_chars:
            continue
        if first is None:
            first = block
        else:
            lines.append(block)
        used += len(block)
    if first is None:
        return Answer(text="", citations=(), abstained=True, reason="no_sentences")
    text = "结论：" + first + ("\n" + "\n".join(lines) if lines else "")
    citations = _citations_from_text(text, hits)
    if not citations:
        return Answer(text=text, citations=(), abstained=False, reason="dump_no_citation")
    return Answer(text=text, citations=citations, abstained=False, reason="dump_compose")


__all__ = ["answer_with_dump", "MAX_ANSWER_CHARS", "MAX_HITS"]
