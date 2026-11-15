"""Section/clause expansion for the standard RAG evidence pack.

Retrieval often lands on the right document but the wrong clause. This module
adds adjacent chunks from the same document and gives legal/operative clauses a
small ranking prior over background prose. It is opt-in and never touches the
dump/acceptance arm.
"""

from __future__ import annotations

import re
from typing import Any

CLAUSE_MARKERS = (
    "法律责任",
    "处罚",
    "罚款",
    "没收",
    "吊销",
    "责令",
    "禁止",
    "应当",
    "名录",
    "标准",
    "第",
)
BACKGROUND_MARKERS = ("前言", "目录", "背景", "说明", "附录", "参考文献")
ARTICLE_RE = re.compile(r"第[一二三四五六七八九十百千0-9]+条")


def clause_priority(chunk: Any) -> int:
    text = f"{getattr(chunk, 'section', '')} {getattr(chunk, 'text', '')}"
    score = 2 if ARTICLE_RE.search(text) else 0
    score += sum(1 for marker in CLAUSE_MARKERS if marker in text)
    score -= sum(1 for marker in BACKGROUND_MARKERS if marker in text)
    return score


def expand_neighbors(
    hits: list[Any],
    chunks: list[Any],
    *,
    neighbors: int = 1,
    clause_rank: bool = True,
) -> list[Any]:
    """Add up to ``neighbors`` adjacent chunks per hit from the same document."""
    if neighbors <= 0 and not clause_rank:
        return list(hits)
    by_doc: dict[str, list[Any]] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    for doc_chunks in by_doc.values():
        doc_chunks.sort(key=lambda chunk: (chunk.page, chunk.char_start, chunk.chunk_id))
    index = {
        chunk.chunk_id: (chunk.doc_id, position)
        for doc_id, rows in by_doc.items()
        for position, chunk in enumerate(rows)
    }
    selected: dict[str, Any] = {}
    for hit in hits:
        selected[hit.chunk.chunk_id] = hit
        position = index.get(hit.chunk.chunk_id)
        if position is None or neighbors <= 0:
            continue
        doc_id, position = position
        rows = by_doc[doc_id]
        for offset in range(1, neighbors + 1):
            for candidate_position in (position - offset, position + offset):
                if 0 <= candidate_position < len(rows):
                    chunk = rows[candidate_position]
                    selected.setdefault(chunk.chunk_id, type(hit)(chunk=chunk, score=hit.score))
    expanded = list(selected.values())
    if clause_rank:
        expanded.sort(
            key=lambda hit: (
                -clause_priority(hit.chunk),
                -hit.score,
            )
        )
    return expanded


__all__ = [
    "ARTICLE_RE",
    "BACKGROUND_MARKERS",
    "CLAUSE_MARKERS",
    "clause_priority",
    "expand_neighbors",
]
