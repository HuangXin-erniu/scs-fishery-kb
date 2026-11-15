from __future__ import annotations

from scs_fkb.answer_v3.llm_answer import _resolve_citations
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.rag import _citations_from_text


def _hit() -> SearchHit:
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-X-001",
        source_id="POL-X-001",
        page=1,
        section="第四十条",
        text="测试条款",
        token_count=4,
        char_start=0,
        char_end=4,
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_tolerant_resolution_accepts_same_document_other_section() -> None:
    text = "结论 [POL-X-001 §第四十二条]"
    assert _resolve_citations(text, [_hit()])[0] is False
    assert _resolve_citations(text, [_hit()], tolerant=True)[0] is True


def test_tolerant_citation_extraction_accepts_same_document_other_section() -> None:
    text = "结论 [POL-X-001 §第四十二条]"
    assert _citations_from_text(text, [_hit()]) == []
    citations = _citations_from_text(text, [_hit()], tolerant=True)
    assert len(citations) == 1
    assert citations[0].doc_id == "POL-X-001"
