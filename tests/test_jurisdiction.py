from __future__ import annotations

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.service_v2.answer import _prefer_national


def _hit(doc_id: str, level: str, index: int) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"CH-{index}",
        doc_id=doc_id,
        source_id=doc_id,
        page=1,
        section="一、总则",
        text="测试条款",
        token_count=4,
        char_start=0,
        char_end=4,
        sensitivity="public",
        level=level,
        authority_tier="A",
    )
    return SearchHit(chunk=chunk, score=1.0 - index / 10)


def test_prefer_national_puts_national_first_when_three_exist() -> None:
    hits = [
        _hit("POL-GD-001", "provincial", 0),
        _hit("POL-LAW-001", "national", 1),
        _hit("POL-LAW-002", "national", 2),
        _hit("POL-LAW-003", "national", 3),
    ]
    ordered = _prefer_national(hits)
    assert [hit.chunk.doc_id for hit in ordered[:3]] == [
        "POL-LAW-001",
        "POL-LAW-002",
        "POL-LAW-003",
    ]
    assert ordered[-1].chunk.doc_id == "POL-GD-001"


def test_prefer_national_keeps_order_with_too_few_national_hits() -> None:
    hits = [_hit("POL-GD-001", "provincial", 0), _hit("POL-LAW-001", "national", 1)]
    assert [hit.chunk.doc_id for hit in _prefer_national(hits)] == ["POL-GD-001", "POL-LAW-001"]
