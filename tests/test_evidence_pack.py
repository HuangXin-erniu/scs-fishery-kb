from __future__ import annotations

from datetime import date

from scs_fkb.answer_v3.evidence import EvidenceItem, build_evidence_pack
from scs_fkb.models import Chunk, SearchHit


def _chunk(
    text: str = "南海区伏季休渔时间为5月1日12时至8月16日12时。",
    *,
    doc_id: str = "POL-CLOS-015",
    section: str = "三、休渔时间",
    page: int = 3,
    chunk_id: str = "CH-1",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_id=doc_id,
        page=page,
        section=section,
        text=text,
        token_count=20,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        authority_tier="A",
        level="national",
    )


def test_pack_carries_label_and_metadata() -> None:
    registry = {
        "POL-CLOS-015": {
            "title": "南海区伏季休渔通告",
            "authority_tier": "A",
            "currency": {"as_of": "2026-11-02", "review_due": "2026-12-02"},
            "ingest": {"tier": "canonical"},
        }
    }
    pack = build_evidence_pack(
        [SearchHit(chunk=_chunk(), score=1.0)],
        registry=registry,
        index_version="idx-1",
        today=date(2026, 11, 12),
    )
    assert len(pack.items) == 1
    item = pack.items[0]
    assert item.label == "POL-CLOS-015 §三、休渔时间 p.3"
    assert item.title == "南海区伏季休渔通告"
    assert item.authority_tier == "A"
    assert item.as_of == "2026-11-02"
    assert item.stale is False
    assert item.provisional is False
    assert pack.chars == len(pack.text)
    assert pack.index_version == "idx-1"
    assert pack.by_label[item.label] is item


def test_pack_flags_stale_and_provisional() -> None:
    registry = {
        "POL-CLOS-015": {
            "currency": {"review_due": "2026-01-01"},
            "ingest": {"tier": "provisional"},
        }
    }
    pack = build_evidence_pack(
        [SearchHit(chunk=_chunk(), score=1.0)],
        registry=registry,
        today=date(2026, 11, 12),
    )
    assert pack.items[0].stale is True
    assert pack.items[0].provisional is True
    assert pack.stale_docs == ["POL-CLOS-015"]
    assert pack.provisional is True


def test_pack_deduplicates_and_caps_items() -> None:
    hits = [
        SearchHit(
            chunk=_chunk(
                text=f"休渔时间第{index}条：{index + 1}月1日12时起。",
                chunk_id=f"CH-{index}",
            ),
            score=1.0 - index / 10,
        )
        for index in range(5)
    ]
    pack = build_evidence_pack(hits, max_items=3)
    assert len(pack.items) == 3
    assert pack.truncated is True
    duplicate = [hits[0], hits[0]]
    deduped = build_evidence_pack(duplicate)
    assert len(deduped.items) == 1


def test_pack_caps_characters() -> None:
    long_text = "休渔期为5月1日12时至8月16日12时。" * 200
    pack = build_evidence_pack(
        [SearchHit(chunk=_chunk(text=long_text), score=1.0)],
        max_chars=100,
        quote_chars=10_000,
    )
    assert pack.chars <= 100 or pack.items == ()


def test_evidence_item_serializes_for_cache() -> None:
    pack = build_evidence_pack([SearchHit(chunk=_chunk(), score=1.0)])
    row = pack.to_models()[0]
    assert row["doc_id"] == "POL-CLOS-015"
    assert row["section"] == "三、休渔时间"
    item = EvidenceItem(
        chunk=pack.items[0].chunk,
        quote=pack.items[0].quote,
        score=pack.items[0].score,
        rank=0,
    )
    assert item.to_dict()["chunk_id"] == "CH-1"
