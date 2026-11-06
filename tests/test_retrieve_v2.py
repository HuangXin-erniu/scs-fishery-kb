from __future__ import annotations

from scs_fkb.bm25 import BM25Index
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.retrieve_v2 import HybridRetriever, Reranker, RetrievalFilters, plan_query
from scs_fkb.retrieve_v2.filters import filter_hits


def _chunk(
    chunk_id: str,
    text: str,
    *,
    doc_id: str = "POL-T-001",
    sensitivity: str = "public",
    authority_tier: str = "A",
    level: str = "national",
    jurisdiction: str = "national",
    effective_from: str = "",
    effective_to: str = "",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_id=doc_id,
        page=0,
        section="第一条",
        text=text,
        token_count=len(text),
        char_start=0,
        char_end=len(text),
        sensitivity=sensitivity,
        authority_tier=authority_tier,
        level=level,
        jurisdiction=jurisdiction,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def _hits(chunks: list[Chunk]) -> list[SearchHit]:
    return [SearchHit(chunk=chunk, score=1.0 - index * 0.1) for index, chunk in enumerate(chunks)]


def test_filters_sensitivity_authority_and_effective_date() -> None:
    public = _chunk("a", "公开文本")
    internal = _chunk("b", "内部文本", sensitivity="internal")
    municipal = _chunk("c", "地方文本", authority_tier="C", level="municipal")
    expired = _chunk("d", "旧文本", effective_to="2025-12-31")
    filters = RetrievalFilters(
        sensitivity_ceiling="public",
        authority_tiers=("A", "B"),
        levels=("national",),
        as_of="2026-11-06",
    )
    assert filters.matches(public)
    assert not filters.matches(internal)
    assert not filters.matches(municipal)
    assert not filters.matches(expired)
    assert filter_hits(_hits([public, internal]), filters) == _hits([public])


def test_filters_allow_internal_when_ceiling_is_internal() -> None:
    internal = _chunk("b", "内部文本", sensitivity="internal")
    assert RetrievalFilters(sensitivity_ceiling="internal").matches(internal)


def test_router_extracts_nature_region_and_year() -> None:
    plan = plan_query("广西2026年伏季休渔的时间是什么？")
    assert plan.nature in {"rule", "status", "definition"}
    assert plan.region == "guangxi"
    assert plan.year == 2026
    assert plan.freshness is True


def test_router_falls_back_to_general() -> None:
    plan = plan_query("今天天气怎么样？")
    assert plan.domain == "general"
    assert plan.region is None


def test_reranker_orders_candidates() -> None:
    chunks = [_chunk("a", "无关文本"), _chunk("b", "休渔时间")]
    hits = _hits(chunks)
    reranker = Reranker(scorer=lambda query, texts: [0.1 for _ in texts])
    reranker._scorer = lambda query, texts: [0.9 if "休渔" in text else 0.1 for text in texts]
    ranked = reranker.rerank("休渔", hits, top_k=2)
    assert ranked[0].chunk.chunk_id == "b"
    assert ranked[0].score == 0.9


def test_hybrid_retriever_fuses_lexical_and_injected_dense() -> None:
    chunks = [
        _chunk("a", "南海区伏季休渔时间为五月一日至八月十六日。"),
        _chunk("b", "捕捞许可证申请需要提交申请书和证书。"),
        _chunk("c", "渔港内不得装卸危险货物。"),
    ]
    bm25 = BM25Index(chunks)
    retriever = HybridRetriever(
        chunks,
        bm25,
        dense_fn=lambda query, depth: [("b", 0.9), ("a", 0.4)],
        reranker=None,
        depth=10,
    )
    hits = retriever.search("休渔时间", top_k=3)
    assert hits
    assert hits[0].chunk.chunk_id in {"a", "b"}


def test_hybrid_retriever_applies_filter_before_return() -> None:
    chunks = [
        _chunk("a", "南海区休渔时间", sensitivity="public"),
        _chunk("b", "南海区休渔时间", sensitivity="internal"),
    ]
    bm25 = BM25Index(chunks)
    retriever = HybridRetriever(chunks, bm25, dense_fn=lambda q, d: [], depth=10)
    hits = retriever.search("休渔", top_k=5, filters=RetrievalFilters(sensitivity_ceiling="public"))
    assert [hit.chunk.chunk_id for hit in hits] == ["a"]
