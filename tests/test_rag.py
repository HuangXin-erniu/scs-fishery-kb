from __future__ import annotations

from pathlib import Path

from scs_fkb.llm import LLMConfig
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.rag import (
    LLMCache,
    generate_answer,
    judge_evidence,
    llm_answer_fn,
    public_hits,
    score_answer,
)


def _hit(
    doc: str = "POL-LAW-009",
    section: str = "第七十八条",
    sensitivity: str = "public",
    text: str = "违反禁渔区、禁渔期的规定从事捕捞活动，处二十万元以下的罚款。",
) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"{doc}-0000",
        doc_id=doc,
        source_id=doc,
        page=0,
        section=section,
        text=text,
        token_count=10,
        char_start=0,
        char_end=len(text),
        sensitivity=sensitivity,
    )
    return SearchHit(chunk=chunk, score=0.9)


class _FakeClient:
    def __init__(self, replies: list[dict]) -> None:
        self.replies = list(replies)
        self.calls = 0
        self.config = LLMConfig(
            base_url="https://example.test/v1",
            api_key="secret",
            model="deepseek-v4.1-flash",
            reasoning_effort="low",
            session="test",
        )

    def chat_json(self, messages, *, temperature=0.0, max_tokens=1200):
        self.calls += 1
        return self.replies.pop(0)


def test_public_hits_drops_internal() -> None:
    hits = [_hit(), _hit(sensitivity="internal")]
    assert [hit.chunk.sensitivity for hit in public_hits(hits)] == ["public"]


def test_generate_answer_requires_valid_citation(tmp_path: Path) -> None:
    hit = _hit()
    client = _FakeClient(
        [
            {
                "abstained": False,
                "answer": "违反禁渔区规定捕捞的，处二十万元以下罚款 [POL-LAW-009 §第七十八条].",
                "reason": "",
            }
        ]
    )
    answer = generate_answer("休渔期违规怎么处罚？", [hit], client, LLMCache(tmp_path))
    assert not answer.abstained
    assert answer.citations[0].doc_id == "POL-LAW-009"


def test_generate_answer_rejects_unknown_citation() -> None:
    client = _FakeClient(
        [
            {
                "abstained": False,
                "answer": "处二十万元以下罚款 [POL-LAW-009 §不存在].",
                "reason": "",
            }
        ]
    )
    answer = generate_answer("休渔期违规怎么处罚？", [_hit()], client)
    assert answer.abstained
    assert answer.reason.startswith("llm_citation_invalid")


def test_judge_and_answer_fn_abstain_when_evidence_is_off_topic() -> None:
    client = _FakeClient([{"answerable": False, "reason": "no historical record"}])
    judged = judge_evidence("某渔场历史渔汛是什么？", [_hit()], client)
    assert judged["answerable"] is False

    client = _FakeClient([{"answerable": False, "reason": "no historical record"}])
    answer = llm_answer_fn(client)("某渔场历史渔汛是什么？", [_hit()])
    assert answer.abstained
    assert client.calls == 1


def test_cache_reuses_reply(tmp_path: Path) -> None:
    client = _FakeClient([{"answerable": True, "reason": "yes"}])
    cache = LLMCache(tmp_path)
    first = judge_evidence("休渔期违规怎么处罚？", [_hit()], client, cache)
    second = judge_evidence("休渔期违规怎么处罚？", [_hit()], client, cache)
    assert first == second
    assert client.calls == 1


def test_score_answer_clamps_values() -> None:
    client = _FakeClient(
        [{"correctness": 1.4, "completeness": -0.2, "faithfulness": 0.8, "reason": "ok"}]
    )
    scores = score_answer("休渔期违规怎么处罚？", ["处二十万元以下罚款"], "答案", "证据", client)
    assert scores["correctness"] == 1.0
    assert scores["completeness"] == 0.0
    assert scores["faithfulness"] == 0.8
