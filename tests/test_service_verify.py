from __future__ import annotations

import pytest

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.service_v2 import AnswerService


def _hit() -> SearchHit:
    text = "南海区伏季休渔时间为5月1日12时至8月16日12时。"
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
        source_id="POL-CLOS-015",
        page=1,
        section="三、休渔时间",
        text=text,
        token_count=20,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        kind="corpus",
    )
    return SearchHit(chunk=chunk, score=1.0)


class _Retriever:
    index_version = "v2-test"

    def search(self, question: str, top_k: int = 5, filters=None, rerank: bool = True):
        return [_hit()]

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        return True


def test_the_dump_path_does_not_run_the_five_hit_sufficiency_judge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dump arm decides answerability on its own candidate set, not on five hits."""
    monkeypatch.setenv("SCS_FKB_ANSWER_MODE", "dump")
    monkeypatch.setenv("SCS_FKB_SUMMARY_MODE", "off")
    monkeypatch.setenv("SCS_FKB_VERIFY_ANSWERS", "on")

    def _boom(self, question, hits):  # noqa: ANN001, ARG001
        raise AssertionError("the dump path must not call the sufficiency judge")

    monkeypatch.setattr(AnswerService, "_sufficiency", _boom)
    result = AnswerService(retriever=_Retriever(), playbooks=[], facts=[]).query(
        "2026年南海区伏季休渔从什么时候开始？"
    )
    assert result.abstained is False
    assert "休渔" in result.summary
