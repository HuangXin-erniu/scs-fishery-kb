from __future__ import annotations

from scs_fkb.answer import answer_question
from scs_fkb.models import Chunk, SearchHit


def _hit(
    kind: str, text: str = "休渔时间 5月1日12时至8月16日12时", score: float = 1.0
) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"{kind}-1",
        doc_id="POL-CLOS-015" if kind == "corpus" else f"WEB-{kind.upper()}-1",
        source_id="POL-CLOS-015" if kind == "corpus" else f"WEB-{kind.upper()}-1",
        page=0,
        section="三、休渔时间",
        text=text,
        token_count=8,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        url="" if kind == "corpus" else "https://example.invalid/x",
        retrieved_at="" if kind == "corpus" else "2026-11-03",
        kind=kind,
    )
    return SearchHit(chunk=chunk, score=score)


QUESTION = "休渔时间是什么？"


def test_corpus_hit_passes() -> None:
    answer = answer_question(
        QUESTION, [_hit("corpus")], min_score=0.5, min_matched=1, require_corpus=True
    )
    assert not answer.abstained


def test_web_only_abstains() -> None:
    answer = answer_question(
        QUESTION, [_hit("web")], min_score=0.5, min_matched=1, require_corpus=True
    )
    assert answer.abstained
    assert answer.reason == "no_corpus_evidence"


def test_note_only_abstains() -> None:
    answer = answer_question(
        QUESTION, [_hit("note")], min_score=0.5, min_matched=1, require_corpus=True
    )
    assert answer.abstained
    assert answer.reason == "no_corpus_evidence"


def test_flag_off_allows_web() -> None:
    answer = answer_question(
        QUESTION, [_hit("web")], min_score=0.5, min_matched=1, require_corpus=False
    )
    assert not answer.abstained
