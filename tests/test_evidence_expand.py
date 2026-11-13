from __future__ import annotations

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.retrieve_v2.expand import expand_neighbors


def _hit(chunk_id: str, doc_id: str, text: str, char_start: int) -> SearchHit:
    chunk = Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_id=doc_id,
        page=1,
        section="第一条",
        text=text,
        token_count=8,
        char_start=char_start,
        char_end=char_start + len(text),
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_expand_adds_adjacent_chunks_from_same_document() -> None:
    chunks = [
        _hit("A1", "DOC-A", "背景说明", 0).chunk,
        _hit("A2", "DOC-A", "第一条 禁止非法捕捞", 10).chunk,
        _hit("A3", "DOC-A", "第二条 法律责任", 20).chunk,
    ]
    hits = [_hit("A2", "DOC-A", "第一条 禁止非法捕捞", 10)]
    expanded = expand_neighbors(hits, chunks, neighbors=1, clause_rank=False)
    assert {hit.chunk.chunk_id for hit in expanded} == {"A1", "A2", "A3"}


def test_clause_rank_puts_legal_clause_first() -> None:
    chunks = [
        _hit("A1", "DOC-A", "背景说明", 0).chunk,
        _hit("A2", "DOC-A", "第一条 禁止非法捕捞", 10).chunk,
        _hit("A3", "DOC-A", "第二条 法律责任 罚款", 20).chunk,
    ]
    expanded = expand_neighbors(
        [_hit("A1", "DOC-A", "背景说明", 0)], chunks, neighbors=2, clause_rank=True
    )
    assert expanded[0].chunk.chunk_id == "A3"
