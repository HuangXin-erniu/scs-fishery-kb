from __future__ import annotations

import pytest

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.service_v2 import AnswerService


def _hit() -> SearchHit:
    text = "因台风、风暴潮等造成渔业损失的，按属地灾害救助政策申请补助。"
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-SUB-094",
        source_id="POL-SUB-094",
        page=4,
        section="三、补助范围",
        text=text,
        token_count=24,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        kind="corpus",
        authority_tier="A",
    )
    return SearchHit(chunk=chunk, score=1.0)


class _Retriever:
    index_version = "v2-test"

    def __init__(self) -> None:
        self.hits = [_hit()]

    def search(self, question: str, top_k: int = 5, filters=None, rerank: bool = True):
        return self.hits

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        return True


@pytest.fixture(autouse=True)
def _dump_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCS_FKB_ANSWER_MODE", "dump")
    monkeypatch.setenv("SCS_FKB_SUMMARY_MODE", "off")


def _service() -> AnswerService:
    return AnswerService(retriever=_Retriever(), playbooks=[], facts=[])


def test_a_policy_question_that_mentions_a_typhoon_is_answered():
    result = _service().query("台风过后网具损坏有没有补助政策？")
    assert result.mode != "clarify"
    assert result.reason != "clarify"
    assert result.abstained is False


def test_a_genuinely_vague_question_is_still_clarified():
    result = _service().query("某渔场今年怎么样？")
    assert result.mode == "clarify"
    assert result.abstained is True
