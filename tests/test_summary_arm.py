from __future__ import annotations

from types import SimpleNamespace

import pytest

from scs_fkb.answer_v3.channels import ChannelBook
from scs_fkb.answer_v3.compose import compose
from scs_fkb.answer_v3.select import Clause
from scs_fkb.answer_v3.summary_arm import summarize
from scs_fkb.llm import LLMError


class FakeClient:
    """Scripted chat client: each call returns the next reply."""

    def __init__(self, replies: list[object]) -> None:
        self.replies = list(replies)
        self.calls = 0
        self.config = SimpleNamespace(model="fake-model")

    def chat(self, messages, *, temperature: float = 0.0, max_tokens: int = 1200, **kwargs):
        self.calls += 1
        if not self.replies:
            raise LLMError("no scripted reply")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


CLAUSES = (
    Clause(
        text="违反禁渔期规定进行捕捞的，没收渔获物和违法所得，并处5万元以下的罚款。",
        doc_id="POL-LAW-009",
        section="第七十八条",
        page=12,
        rank=0,
        source_class="normative",
    ),
    Clause(
        text="捕捞许可证的有效期为5年，有效期届满需要延续的，应当在届满前3个月提出申请。",
        doc_id="POL-STD-010",
        section="第三十五条",
        page=3,
        rank=1,
        source_class="normative",
    ),
)

QUESTION = "休渔期下网怎么罚？许可证几年有效？"


def _summary(
    conclusion: str, points: list[str] | None = None, gaps: list[str] | None = None
) -> str:
    import json

    return json.dumps(
        {"conclusion": conclusion, "points": points or [], "gaps": gaps or []}, ensure_ascii=False
    )


def test_a_valid_draft_keeps_its_citation():
    client = FakeClient(
        [
            _summary(
                "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。",
                ["捕捞许可证有效期为5年 [POL-STD-010 §第三十五条]。"],
            ),
            '{"supported": true, "reason": "ok"}',
        ]
    )
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    assert "5万元" in draft.conclusion
    assert draft.points
    assert draft.citations
    assert draft.repaired is False


def test_a_citation_to_an_unsupplied_section_is_repaired_once():
    client = FakeClient(
        [
            _summary("违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第九十九条]。"),
            '{"answer": "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。"}',
            '{"supported": true, "reason": "ok"}',
        ]
    )
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    assert draft.repaired is True
    assert "第七十八条" in draft.conclusion
    assert client.calls >= 3


def test_an_ungrounded_number_cannot_reach_the_user():
    client = FakeClient(
        [
            _summary("违反禁渔期规定捕捞的，并处10万元以下罚款 [POL-LAW-009 §第七十八条]。"),
            '{"answer": "违反禁渔期规定捕捞的，并处10万元以下罚款 [POL-LAW-009 §第七十八条]。"}',
        ]
    )
    assert summarize(QUESTION, CLAUSES, client) is None


def test_a_failing_client_falls_back_to_none():
    client = FakeClient([LLMError("timeout")])
    assert summarize(QUESTION, CLAUSES, client) is None


def test_no_client_or_no_clauses_returns_none():
    assert summarize(QUESTION, CLAUSES, None) is None
    assert summarize(QUESTION, (), FakeClient([])) is None


def test_compose_renders_the_draft_as_conclusion_and_points():
    client = FakeClient(
        [
            _summary(
                "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。",
                ["捕捞许可证有效期为5年 [POL-STD-010 §第三十五条]。"],
                ["休渔期具体起止：已登记语料未覆盖"],
            ),
            '{"supported": true, "reason": "ok"}',
        ]
    )
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    contract = compose(
        QUESTION,
        "\n".join(clause.rendered() for clause in CLAUSES),
        doc_ids=["POL-LAW-009", "POL-STD-010"],
        registry={},
        channels=ChannelBook.load(),
        draft=draft,
    )
    assert contract.conclusion.startswith("违反禁渔期规定捕捞的")
    assert "要点：" in contract.body
    assert any("未覆盖" in item for item in contract.gap)
    assert contract.slots and contract.slots[0].doc_id == "POL-LAW-009"
    assert contract.answerability == "partial"
    assert contract.summary_source == "model"
    assert contract.to_dict()["summary_source"] == "model"


def test_compose_without_a_draft_still_uses_the_text_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCS_FKB_SUMMARY_SELECT", "off")
    contract = compose(
        "捕捞许可证几年有效？",
        "捕捞许可证的有效期为5年。 [POL-STD-010 §第三十五条]",
        doc_ids=["POL-STD-010"],
        registry={},
        channels=ChannelBook.load(),
    )
    assert contract.conclusion
    assert contract.slots == ()
    assert contract.summary_source == "deterministic"


def test_compose_records_a_dropped_draft_as_fallback():
    """A draft that failed the checks is reported as fallback, not as a model answer."""
    contract = compose(
        "捕捞许可证几年有效？",
        "捕捞许可证的有效期为5年。 [POL-STD-010 §第三十五条]",
        doc_ids=["POL-STD-010"],
        registry={},
        channels=ChannelBook.load(),
        draft=None,
        draft_status="fallback",
    )
    assert contract.summary_source == "fallback"
