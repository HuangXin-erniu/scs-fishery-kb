from __future__ import annotations

from scs_fkb.answer_v3.select import (
    Clause,
    gaps_of,
    select_slots,
    slot_kind,
    split_slots,
)


def _clause(
    text: str, doc: str = "POL-STD-010", section: str = "第三十五条", rank: int = 0
) -> Clause:
    return Clause(text=text, doc_id=doc, section=section, page=1, rank=rank)


def test_split_keeps_at_most_three_typed_slots():
    slots = split_slots("捕捞许可证能用几年？到期前多久去换？过期了还能补吗？现在还能办吗？")
    assert len(slots) == 3
    assert [item.kind for item in slots] == ["numeric", "time", "boolean"]
    assert slots[0].unit == "年"


def test_slot_kinds_cover_the_fixture_questions():
    assert slot_kind("休渔期抓到一条拖网船在海里下网，按哪条罚？") == "basis"
    assert slot_kind("船和网能不能没收？") == "boolean"
    assert slot_kind("要交哪些材料？") == "enum"
    assert slot_kind("补助资金追回的程序是什么？") == "procedure"
    assert slot_kind("材料递县里还是省里？") == "body"


def test_numeric_slot_takes_the_asked_unit_not_the_neighbour():
    clauses = (
        _clause("捕捞许可证的有效期为5年。", rank=0),
        _clause("有效期届满前3个月，应当申请换发。", section="第三十六条", rank=1),
        _clause("未按期换发的，可以补办。", section="第三十七条", rank=2),
    )
    selected = select_slots("捕捞许可证能用几年？", clauses, rerank=False, min_score=0.0)
    assert selected[0].answered
    assert "5年" in selected[0].clause.text
    assert "3个月" not in selected[0].clause.text


def test_boolean_slot_rejects_a_clause_without_a_modal():
    clauses = (
        _clause("情节严重的，没收渔具和渔船。", doc="POL-LAW-009", section="第七十八条", rank=0),
        _clause("可以没收船舶。", doc="POL-LAW-009", section="第七十八条", rank=1),
    )
    selected = select_slots("船和网能不能没收？", clauses, rerank=False, min_score=0.0)
    assert selected[0].answered
    assert "可以" in selected[0].clause.text


def test_slot_without_a_satisfying_clause_becomes_a_gap():
    clauses = (_clause("渔业行政主管部门应当建立台账。", rank=0),)
    selected = select_slots("罚款多少钱？", clauses, rerank=False, min_score=0.0)
    assert not selected[0].answered
    assert selected[0].reason == "no_candidate"
    assert gaps_of(selected)[0].startswith("罚款多少钱")


def test_selection_is_deterministic():
    clauses = (
        _clause("渔业捕捞许可证有效期为五年。", rank=0),
        _clause("渔业捕捞许可证有效期届满前三个月申请换发。", section="第三十六条", rank=1),
    )
    first = select_slots("捕捞许可证有效几年？", clauses, rerank=False, min_score=0.0)
    second = select_slots("捕捞许可证有效几年？", clauses, rerank=False, min_score=0.0)
    assert first == second


def test_normative_source_beats_reference_at_equal_overlap():
    text = "拖网渔船应当持有捕捞许可证。"
    clauses = (
        Clause(text=text, doc_id="PAPER-105", section="p.2", rank=0, source_class="reference"),
        Clause(text=text, doc_id="POL-STD-010", section="第三条", rank=1, source_class="normative"),
    )
    selected = select_slots("拖网渔船要许可证吗？", clauses, rerank=False, min_score=0.0)
    assert selected[0].clause is not None
    assert selected[0].clause.doc_id == "POL-STD-010"


def test_long_clause_is_tightened_to_a_verbatim_window():
    filler = "各级渔业主管部门应当加强日常巡查和台账管理，" * 6
    text = filler + "违反禁渔期规定的，处五万元罚款。"
    selected = select_slots("违反禁渔期罚多少？", (_clause(text),), rerank=False, min_score=0.0)
    assert selected[0].clause is not None
    assert len(selected[0].clause.text) <= 160
    assert selected[0].clause.text in text
