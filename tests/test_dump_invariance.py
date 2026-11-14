from __future__ import annotations

import hashlib

from scs_fkb.answer_v3.dump_arm import answer_with_dump
from scs_fkb.models import Chunk, SearchHit

TEXT = (
    "（一）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。"
    "（二）其他海域为5月1日12时至9月16日12时。"
)
CHUNK = Chunk(
    chunk_id="c1",
    doc_id="POL-CLOS-015",
    source_id="SRC-CLOS",
    page=3,
    section="三、休渔时间",
    text=TEXT,
    token_count=48,
    char_start=0,
    char_end=len(TEXT),
    sensitivity="public",
    source_class="normative",
)


class _Retriever:
    depth = 0

    def search(self, question: str, top_k: int = 5) -> list[SearchHit]:
        return [SearchHit(chunk=CHUNK, score=1.0)]


def _answer():
    return answer_with_dump("休渔时间到什么时候？", _Retriever(), max_hits=3, with_numbers=False)


def test_evidence_text_is_locked():
    """The acceptance run scores this text; it must not drift with summary work."""
    answer = _answer()
    digest = hashlib.sha256(answer.text.encode("utf-8")).hexdigest()
    assert digest == "e0d91522e5794dbe4b9b70bf7473a85716c1a8f72d30d35da3aa9beb4a2be0d9"
    assert answer.text.startswith("（一）北纬26度30分至北纬12度")
    assert "依据摘录" not in answer.text


def test_clauses_are_attached_without_changing_the_text():
    answer = _answer()
    assert answer.clauses
    assert all(clause.text in answer.text for clause in answer.clauses)
    assert {clause.doc_id for clause in answer.clauses} == {"POL-CLOS-015"}
