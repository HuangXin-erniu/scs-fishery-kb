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


PAGE_CLAUSES = (
    Clause(
        text="本文件适用于卫星遥感远洋渔场环境监测产品的制作与分发。",
        doc_id="POL-OCEAN-096",
        section="",
        page=7,
        rank=0,
        source_class="normative",
    ),
)


def test_a_page_written_as_a_section_still_resolves():
    client = FakeClient(
        [
            _summary("监测产品适用于远洋渔业生产与科研 [POL-OCEAN-096 §p.7]。"),
            '{"supported": true, "reason": "ok"}',
        ]
    )
    draft = summarize("监测产品适用哪些单位？", PAGE_CLAUSES, client)
    assert draft is not None
    assert draft.citations
    assert client.calls >= 2


def test_a_gap_sentence_is_not_an_uncited_claim():
    client = FakeClient(
        [
            _summary("休渔期不出海是否发放油补，目前证据未规定 [POL-OCEAN-096 §p.7]。"),
        ]
    )
    draft = summarize("休渔期不出海发不发油补？", PAGE_CLAUSES, client)
    assert draft is not None
    assert "未规定" in draft.conclusion
    # The verifier is skipped for a pure gap draft, so only one call was made.
    assert client.calls == 1


def test_a_factual_uncited_sentence_is_still_rejected():
    client = FakeClient(
        [
            _summary("休渔期不出海可以领取油补，金额为每年两万元。"),
            '{"answer": "休渔期不出海能否领取油补，目前证据未规定 [POL-OCEAN-096 §p.7]。"}',
            '{"supported": true, "reason": "ok"}',
        ]
    )
    draft = summarize("休渔期不出海发不发油补？", PAGE_CLAUSES, client)
    assert draft is not None
    assert "未规定" in draft.conclusion


def test_diagnostics_record_the_failing_stage():
    trace: dict[str, str] = {}
    summarize("休渔期下网怎么罚？", CLAUSES, None, diagnostics=trace)
    assert trace["stage"] == "no_client"

    trace = {}
    client = FakeClient([LLMError("timeout")])
    summarize("休渔期下网怎么罚？", CLAUSES, client, diagnostics=trace)
    assert trace["stage"] == "llm_error"

    trace = {}
    client = FakeClient([_summary("")])
    summarize("休渔期下网怎么罚？", CLAUSES, client, diagnostics=trace)
    assert trace["stage"] == "empty_conclusion"


def test_a_fallback_never_puts_raw_text_in_the_conclusion(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SCS_FKB_SUMMARY_SELECT", "off")
    raw = "二 内陆渔业资源养 护 补 贴 补贴对象为我省合法内陆捕捞渔船的船舶所有 人"
    contract = compose(
        "休渔期不出海发不发油补？",
        raw + " [POL-OCEAN-096 p.7]",
        doc_ids=["POL-OCEAN-096"],
        registry={},
        channels=ChannelBook.load(),
        draft=None,
        draft_status="fallback",
    )
    from scs_fkb.answer_v3.compose import FALLBACK_NOTE

    assert contract.conclusion == FALLBACK_NOTE
    assert "补贴对象" not in contract.body.split("依据摘录：")[0]
    assert contract.answerability == "partial"
    assert any("未通过校验" in item for item in contract.gap)


def test_a_not_answerable_draft_becomes_an_abstention_with_channels(monkeypatch):
    import json

    monkeypatch.setenv("SCS_FKB_SUMMARY_SELECT", "off")
    reply = json.dumps(
        {
            "conclusion": "证据未覆盖泊位费纠纷的受理规定。",
            "points": [],
            "gaps": ["缺泊位费纠纷的受理层级"],
            "coverage": "none",
        },
        ensure_ascii=False,
    )
    client = FakeClient([reply])
    draft = summarize("渔港泊位费纠纷归渔政管吗？", CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "none"
    contract = compose(
        "渔港泊位费纠纷归渔政管吗？",
        "",
        doc_ids=["POL-LAW-009"],
        registry={},
        channels=ChannelBook.load(),
        draft=draft,
    )
    assert contract.answerability == "abstain"
    assert contract.summary_source == "model_gap"
    assert contract.conclusion == ""
    assert any("泊位费" in item for item in contract.gap)
    assert contract.channel


def test_a_contradictory_not_answerable_flag_is_ignored():
    import json

    reply = json.dumps(
        {
            "conclusion": "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。",
            "points": [],
            "gaps": [],
            "coverage": "none",
        },
        ensure_ascii=False,
    )
    client = FakeClient([reply, '{"supported": true, "reason": "ok"}'])
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "full"


def test_partial_coverage_keeps_the_covered_answer():
    import json

    reply = json.dumps(
        {
            "conclusion": "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。",
            "points": [],
            "gaps": ["缺没收渔船的具体程序"],
            "coverage": "partial",
        },
        ensure_ascii=False,
    )
    client = FakeClient([reply, '{"supported": true, "reason": "ok"}'])
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "partial"
    contract = compose(
        QUESTION,
        "违反禁渔期规定进行捕捞的，没收渔获物和违法所得，并处5万元以下的罚款。"
        " [POL-LAW-009 §第七十八条]",
        doc_ids=["POL-LAW-009"],
        registry={},
        channels=ChannelBook.load(),
        draft=draft,
    )
    assert contract.answerability == "partial"
    assert contract.conclusion
    assert any("没收渔船" in item for item in contract.gap)


def test_a_short_exact_clause_outranks_a_long_weaker_article():
    from scs_fkb.answer_v3.summary_arm import _section_score

    short_exact = _section_score({1: 10.0})
    long_weak = _section_score({1: 5.0, 2: 4.0, 3: 3.0})
    # The old formula summed the three best clauses and gave the long article 12 > 10.
    assert short_exact > long_weak


def test_a_clause_matched_by_two_slots_is_counted_once(monkeypatch):
    import scs_fkb.answer_v3.summary_arm as arm

    clause = Clause(
        text="伏季休渔时间为5月1日12时至8月16日12时。",
        doc_id="POL-CLOS-015",
        section="三、休渔时间",
        page=1,
        rank=0,
    )

    def _lexical(slot, clauses, grams, idf, default):  # noqa: ANN001, ARG001
        return [(7.0, clause)]

    monkeypatch.setattr(arm, "_lexical", _lexical)
    captured: dict[int, float] = {}
    real = arm._section_score

    def _spy(values):  # noqa: ANN001
        captured.update(values)
        return real(values)

    monkeypatch.setattr(arm, "_section_score", _spy)
    hits = arm._section_hits("伏季休渔从什么时候开始？休渔到什么时候结束？", [clause])
    assert hits
    assert len(captured) == 1


def test_breadth_only_breaks_ties():
    from scs_fkb.answer_v3.summary_arm import _section_score

    # Three matching clauses must not add up to more than a single precise clause.
    assert _section_score({1: 10.0, 2: 10.0, 3: 10.0}) < _section_score({1: 10.1})


def test_a_none_reply_with_points_is_partial():
    import json

    reply = json.dumps(
        {
            "conclusion": "证据未覆盖放流尾数的具体数值。",
            "points": ["规模标准由县级以上地方渔业行政主管部门确定 [POL-LAW-009 §第七十八条]。"],
            "gaps": ["缺具体放流尾数"],
            "coverage": "none",
        },
        ensure_ascii=False,
    )
    client = FakeClient([reply, '{"supported": true, "reason": "ok"}'])
    draft = summarize("增殖放流的具体尾数是多少？", CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "partial"
    assert draft.gaps


def test_a_none_reply_without_points_stays_none():
    import json

    reply = json.dumps(
        {
            "conclusion": "证据未覆盖放流尾数的具体数值。",
            "points": [],
            "gaps": ["缺具体放流尾数"],
            "coverage": "none",
        },
        ensure_ascii=False,
    )
    client = FakeClient([reply])
    draft = summarize("增殖放流的具体尾数是多少？", CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "none"
    contract = compose(
        "增殖放流的具体尾数是多少？",
        "",
        doc_ids=["POL-LAW-009"],
        registry={},
        channels=ChannelBook.load(),
        draft=draft,
    )
    assert contract.answerability == "abstain"


def test_a_rejected_draft_abstains_with_the_reason(monkeypatch):
    import json

    good = json.dumps(
        {
            "conclusion": "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。",
            "points": [],
            "gaps": [],
            "coverage": "full",
        },
        ensure_ascii=False,
    )
    rejected = json.dumps(
        {"supported": False, "reason": "证据只规定罚款，未规定没收渔船"}, ensure_ascii=False
    )
    repaired = json.dumps(
        {"answer": "违反禁渔期规定捕捞的，并处5万元以下罚款 [POL-LAW-009 §第七十八条]。"},
        ensure_ascii=False,
    )
    client = FakeClient([good, rejected, repaired, rejected])
    draft = summarize(QUESTION, CLAUSES, client)
    assert draft is not None
    assert draft.coverage == "none"
    assert draft.conclusion == "证据不足以支持结论"
    assert any("未规定没收渔船" in item for item in draft.gaps)
    contract = compose(
        QUESTION,
        "",
        doc_ids=["POL-LAW-009"],
        registry={},
        channels=ChannelBook.load(),
        draft=draft,
    )
    assert contract.answerability == "abstain"
    assert contract.channel


def test_a_transport_error_still_falls_back():
    client = FakeClient([LLMError("empty completion")])
    assert summarize(QUESTION, CLAUSES, client) is None
