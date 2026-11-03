from __future__ import annotations

from scs_fkb.answer import augment_with_external
from scs_fkb.models import Answer, Chunk, SearchHit


def _hit() -> SearchHit:
    text = "外部知识示例：大黄鱼学名 Larimichthys crocea。"
    chunk = Chunk(
        chunk_id="WEB-1",
        doc_id="WEB-WORMS-LARIMICHTHYS-CROCEA",
        source_id="WEB-WORMS-LARIMICHTHYS-CROCEA",
        page=0,
        section="web card",
        text=text,
        token_count=8,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        url="https://www.marinespecies.org/rest/x",
        retrieved_at="2026-11-03",
        kind="web",
        source_class="reference",
        trust="standard",
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_abstained_answer_is_not_augmented() -> None:
    answer = Answer(text="证据不足", abstained=True, reason="weak_evidence")
    assert augment_with_external(answer, [_hit()]) is answer


def test_answer_gets_labelled_external_evidence() -> None:
    answer = Answer(text="语料答案。", citations=[], abstained=False, reason="ok")
    augmented = augment_with_external(answer, [_hit()])
    assert "外部知识（辅助" in augmented.text
    assert "https://www.marinespecies.org/rest/x" in augmented.text
    assert len(augmented.citations) == 1
    assert augmented.text.startswith("语料答案。")


def test_no_external_hits_keeps_answer() -> None:
    answer = Answer(text="语料答案。", abstained=False, reason="ok")
    assert augment_with_external(answer, []) is answer
