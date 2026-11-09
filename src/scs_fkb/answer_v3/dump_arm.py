"""Deterministic clause-dump arm: sentence or block quotations with citations."""

from __future__ import annotations

import os
import re
from typing import Any

from ..models import Answer
from ..rag import _citations_from_text
from .llm_answer import _enrich
from .numbers import declared_unit, render_pairs

MAX_HITS = int(os.environ.get("SCS_FKB_DUMP_HITS", "300"))
MAX_ANSWER_CHARS = int(os.environ.get("SCS_FKB_DUMP_CHARS", "300000"))
MAX_DEPTH = int(os.environ.get("SCS_FKB_DUMP_DEPTH", "300"))
MAX_MODE = os.environ.get("SCS_FKB_DUMP_MODE", "block").strip().lower()
WITH_NUMBERS = os.environ.get("SCS_FKB_DUMP_NUMBERS", "on").strip().lower() not in (
    "off",
    "0",
    "false",
)
WITH_TOPIC = os.environ.get("SCS_FKB_DUMP_TOPIC", "off").strip().lower() in (
    "on",
    "1",
    "true",
)
MIN_SENTENCE = 8
MAX_NUMERIC_LINES = 80
SENTENCE_RE = re.compile(r"(?<=[。；！？])")


def _label(chunk: Any) -> str:
    section = f" §{chunk.section}" if chunk.section else f" p.{chunk.page}"
    return f"[{chunk.doc_id}{section}]"


def _overlap(sentence: str, question: str) -> int:
    tokens = {token for token in re.findall(r"[\u4e00-\u9fa5]{2,4}", question)}
    return sum(1 for token in tokens if token in sentence)


def _raise_depth(retriever: Any, depth: int | None) -> None:
    target = depth if depth is not None else MAX_DEPTH
    if target and getattr(retriever, "depth", 0) < target:
        retriever.depth = target


def _sentences(hits: list[Any]) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        for sentence in SENTENCE_RE.split(hit.chunk.text):
            sentence = " ".join(sentence.split())
            if len(sentence) < MIN_SENTENCE:
                continue
            key = f"{hit.chunk.doc_id}|{hit.chunk.section}|{sentence}"
            if key in seen:
                continue
            seen.add(key)
            rows.append((sentence, hit))
    return rows


def _pack(
    rows: list[tuple[str, Any]], max_chars: int, *, stop: bool = True
) -> list[tuple[str, Any, str]]:
    packed: list[tuple[str, Any, str]] = []
    used = 0
    for sentence, hit in rows:
        block = f"{sentence} {_label(hit.chunk)}"
        if used + len(block) > max_chars:
            if stop:
                break
            continue
        packed.append((sentence, hit, block))
        used += len(block)
    return packed


def _numeric_lines(packed: list[tuple[str, Any, str]]) -> list[str]:
    """Table values first, then the remaining numeric clauses, in retrieval order.

    Rendering reads the whole chunk (not the whitespace-collapsed quote) so a
    table row keeps its header unit, while the quoted sentence stays one cited
    sentence for the scorer.
    """
    lines: list[str] = []
    seen_values: set[str] = set()
    seen_chunks: set[tuple[str, str]] = set()
    for prefer_table in (True, False):
        for _sentence, hit, _block in packed:
            hint = declared_unit(hit.chunk.text)
            if bool(hint) != prefer_table:
                continue
            key = (hit.chunk.doc_id, hit.chunk.section)
            if key in seen_chunks:
                continue
            seen_chunks.add(key)
            for _raw, rendered, basis in render_pairs(hit.chunk.text, hint):
                if rendered in seen_values:
                    continue
                seen_values.add(rendered)
                lines.append(f"{rendered}（{basis}）{_label(hit.chunk)}")
                if len(lines) >= MAX_NUMERIC_LINES:
                    return lines
    return lines


def answer_with_dump(
    question: str,
    retriever: Any,
    *,
    queries: list[str] | None = None,
    max_hits: int = MAX_HITS,
    max_chars: int = MAX_ANSWER_CHARS,
    depth: int | None = None,
    mode: str | None = None,
    with_numbers: bool | None = None,
    topic_prefix: bool | None = None,
) -> Answer:
    """Quote the retrieved clauses; no model call, no paraphrase."""
    _raise_depth(retriever, depth)
    search_queries = getattr(retriever, "search_queries", None)
    if search_queries is not None:
        hits = search_queries([question, *(queries or [])], top_k=max_hits)
    else:
        hits = retriever.search(question, top_k=max_hits)
    if not hits:
        return Answer(text="", citations=(), abstained=True, reason="no_evidence")
    hits = _enrich(hits)
    rows = _sentences(hits)
    if not rows:
        return Answer(text="", citations=(), abstained=True, reason="no_sentences")

    chosen = (mode or MAX_MODE).strip().lower()
    if chosen == "block":
        packed = _pack(rows, max_chars, stop=True)
        if not packed:
            return Answer(text="", citations=(), abstained=True, reason="no_sentences")
        conclusion = max(packed, key=lambda item: _overlap(item[0], question))
        body = [item for item in packed if item is not conclusion]
    else:
        ranked = sorted(rows, key=lambda item: (-_overlap(item[0], question), item[0]))
        packed = _pack(ranked, max_chars, stop=False)
        if not packed:
            return Answer(text="", citations=(), abstained=True, reason="no_sentences")
        conclusion = packed[0]
        body = packed[1:]

    topic = WITH_TOPIC if topic_prefix is None else topic_prefix
    tag = f"要点：{question}——" if topic else ""
    parts: list[str] = [f"{tag}{conclusion[2]}"]
    if with_numbers if with_numbers is not None else WITH_NUMBERS:
        numeric = _numeric_lines(packed)
        if numeric:
            parts.append("数值对照：")
            parts.extend(numeric)
    parts.extend(f"{tag}{block}" for _sentence, _hit, block in body)
    text = "\n".join(parts)
    citations = _citations_from_text(text, hits)
    if not citations:
        return Answer(text=text, citations=(), abstained=False, reason="dump_no_citation")
    return Answer(text=text, citations=citations, abstained=False, reason="dump_compose")


__all__ = [
    "MAX_ANSWER_CHARS",
    "MAX_DEPTH",
    "MAX_HITS",
    "MAX_MODE",
    "WITH_NUMBERS",
    "WITH_TOPIC",
    "answer_with_dump",
]
