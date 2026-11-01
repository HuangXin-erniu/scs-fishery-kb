from __future__ import annotations

import pytest

from scs_fkb.fusion import reciprocal_rank_fusion
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.retrieve import Retriever


def _hit(chunk_id: str, score: float = 1.0) -> SearchHit:
    return SearchHit(
        chunk=Chunk(
            chunk_id=chunk_id,
            doc_id="DOC",
            source_id="DOC",
            page=0,
            section="",
            text=f"text {chunk_id}",
            token_count=2,
            char_start=0,
            char_end=8,
            sensitivity="public",
        ),
        score=score,
    )


def test_rrf_prefers_documents_in_both_lists() -> None:
    lexical = [_hit("a"), _hit("b"), _hit("c")]
    semantic = [_hit("c"), _hit("d"), _hit("a")]
    fused = reciprocal_rank_fusion([lexical, semantic], [1.0, 1.0])
    assert [hit.chunk.chunk_id for hit in fused][:2] == ["a", "c"]


def test_rrf_weights_change_the_order() -> None:
    lexical = [_hit("a"), _hit("b")]
    semantic = [_hit("b"), _hit("a")]
    lexical_first = reciprocal_rank_fusion([lexical, semantic], [2.0, 1.0])
    semantic_first = reciprocal_rank_fusion([lexical, semantic], [1.0, 2.0])
    assert lexical_first[0].chunk.chunk_id == "a"
    assert semantic_first[0].chunk.chunk_id == "b"


def test_rrf_ties_are_deterministic() -> None:
    fused_a = reciprocal_rank_fusion([[_hit("b"), _hit("a")]], [1.0])
    fused_b = reciprocal_rank_fusion([[_hit("b"), _hit("a")]], [1.0])
    assert [hit.chunk.chunk_id for hit in fused_a] == [hit.chunk.chunk_id for hit in fused_b]


def test_rrf_requires_matching_weights() -> None:
    with pytest.raises(ValueError, match="weight"):
        reciprocal_rank_fusion([[_hit("a")]], [1.0, 2.0])


def test_hybrid_requires_a_dense_index() -> None:
    with pytest.raises(ValueError, match="dense"):
        Retriever([], mode="hybrid")


def test_unknown_mode_rejected() -> None:
    with pytest.raises(ValueError, match="mode"):
        Retriever([], mode="magic")


def test_gate_rejects_thin_lexical_evidence() -> None:
    chunk = Chunk(
        chunk_id="a",
        doc_id="D",
        source_id="D",
        page=0,
        section="",
        text="无关内容",
        token_count=2,
        char_start=0,
        char_end=4,
        sensitivity="public",
    )
    retriever = Retriever([chunk], mode="bm25")
    assert not retriever.gate_ok("南海区伏季休渔的起止时间", 19.0, 3)
