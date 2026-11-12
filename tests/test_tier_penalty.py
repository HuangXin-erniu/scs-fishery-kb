from __future__ import annotations

import pytest

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.retrieve_v2.search import PROVISIONAL_FACTOR, _apply_tier_penalty


def _hit(doc_id: str, score: float, tier: str) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"CH-{doc_id}",
        doc_id=doc_id,
        source_id=doc_id,
        page=1,
        section="一",
        text="测试",
        token_count=2,
        char_start=0,
        char_end=2,
        sensitivity="public",
        ingest_tier=tier,
    )
    return SearchHit(chunk=chunk, score=score)


def test_provisional_hit_is_downweighted_below_canonical() -> None:
    hits = [_hit("PROV-1", 0.050, "provisional"), _hit("POL-1", 0.045, "canonical")]
    adjusted = _apply_tier_penalty(hits)
    assert [hit.chunk.doc_id for hit in adjusted] == ["POL-1", "PROV-1"]
    assert adjusted[1].score == pytest.approx(0.050 * PROVISIONAL_FACTOR)


def test_canonical_only_order_is_unchanged() -> None:
    hits = [_hit("POL-1", 0.045, "canonical"), _hit("POL-2", 0.050, "canonical")]
    adjusted = _apply_tier_penalty(hits)
    assert [hit.chunk.doc_id for hit in adjusted] == ["POL-2", "POL-1"]
