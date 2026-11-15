from __future__ import annotations

import pytest

from scs_fkb.answer_v3 import ChannelBook
from scs_fkb.answer_v3.compose import compose
from scs_fkb.answer_v3.select import Clause

REGISTRY = {
    "POL-LAW-009": {
        "source_class": "normative",
        "title_zh": "中华人民共和国渔业法",
        "provenance": {"document_no": "主席令第七十号"},
        "effective": {"from": "2021-07-15"},
    },
    "POL-OTHER": {
        "source_class": "normative",
        "title_zh": "渔港管理条例",
        "provenance": {"document_no": "国务院令第某号"},
        "effective": {"from": "2010-01-01"},
    },
}


@pytest.fixture(autouse=True)
def _no_rerank(monkeypatch: pytest.MonkeyPatch) -> None:
    """The unit tests exercise the lexical path; the cross-encoder is optional."""
    monkeypatch.setenv("SCS_FKB_SUMMARY_RERANK", "off")
    monkeypatch.setenv("SCS_FKB_SUMMARY_SELECT", "on")


def _books() -> ChannelBook:
    return ChannelBook.load()


def test_slots_render_as_key_points_and_stay_verbatim():
    clause = Clause(
        text="情节严重的，并处二十万元以上二百万元以下的罚款，可以没收船舶。",
        doc_id="POL-LAW-009",
        section="第七十八条",
        page=12,
        rank=0,
        source_class="normative",
    )
    answer_text = clause.rendered()
    contract = compose(
        "船和网能不能没收？",
        answer_text,
        doc_ids=["POL-LAW-009"],
        registry=REGISTRY,
        channels=_books(),
        clauses=(clause,),
    )
    assert contract.slots
    assert contract.conclusion == contract.slots[0].text
    assert "可以没收船舶" in contract.conclusion
    assert contract.conclusion.split(" [")[0] in answer_text
    assert "要点：" not in contract.body  # a single slot is the conclusion
    payload = contract.to_dict()
    assert payload["slots"][0]["doc_id"] == "POL-LAW-009"
    assert payload["slots"][0]["kind"] == "boolean"


def test_two_slots_render_a_key_point_line():
    core = Clause(
        text="捕捞许可证的有效期为5年。",
        doc_id="POL-STD-010",
        section="第三十五条",
        rank=0,
        source_class="normative",
    )
    second = Clause(
        text="有效期届满需要继续作业的，应当在有效期届满前3个月申请换发。",
        doc_id="POL-STD-010",
        section="第三十六条",
        rank=1,
        source_class="normative",
    )
    contract = compose(
        "捕捞许可证能用几年？到期前多久去换？",
        "\n".join([core.rendered(), second.rendered()]),
        doc_ids=["POL-STD-010"],
        registry=REGISTRY,
        channels=_books(),
        clauses=(core, second),
    )
    assert len(contract.slots) == 2
    assert "要点：" in contract.body


def test_without_clauses_the_text_path_is_unchanged():
    contract = compose(
        "休渔时间是什么时候？",
        "（一）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。"
        " [POL-CLOS-015 §三、休渔时间]",
        doc_ids=["POL-CLOS-015"],
        registry=REGISTRY,
        channels=_books(),
    )
    assert contract.conclusion
    assert contract.slots == ()


def test_gap_slot_is_declared_instead_of_a_neighbour():
    neighbour = Clause(
        text="渔业行政主管部门应当建立应休渔渔船台账。",
        doc_id="POL-ENF-068",
        section="一、重点任务",
        rank=0,
        source_class="normative",
    )
    contract = compose(
        "过渡渔具过渡期到什么时候？",
        neighbour.rendered(),
        doc_ids=["POL-ENF-068"],
        registry=REGISTRY,
        channels=_books(),
        clauses=(neighbour,),
    )
    assert contract.slots == ()
    assert contract.answerability == "partial"
    assert any("未找到直接规定" in item for item in contract.gap)
