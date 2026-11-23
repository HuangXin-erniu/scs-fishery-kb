from __future__ import annotations

from types import SimpleNamespace

from scs_fkb.answer_v3.slots import answer_slot, answer_with_slots, split_slots


def _hit(doc_id: str, section: str, text: str, score: float = 1.0) -> SimpleNamespace:
    chunk = SimpleNamespace(doc_id=doc_id, page=1, section=section, text=text)
    return SimpleNamespace(chunk=chunk, score=score)


class _Retriever:
    def __init__(self, hits: list[SimpleNamespace]) -> None:
        self.hits = hits

    def search_queries(self, queries: list[str], top_k: int = 6) -> list[SimpleNamespace]:
        return self.hits


def test_split_multi_intent_question_keeps_sub_questions() -> None:
    slots = split_slots("今年休渔还是5月1号到8月16号？北部湾算不算？")
    assert len(slots) >= 2
    assert slots[0].kind == "core"
    assert any("北部湾" in slot.text for slot in slots)


def test_slot_answer_carries_slot_text_and_citation() -> None:
    hits = [
        _hit(
            "POL-CLOS-015",
            "一、休渔海域",
            "休渔海域包括北纬12度以北的南海（含北部湾）海域。",
        )
    ]
    answer = answer_with_slots("北部湾算不算休渔海域？", _Retriever(hits))
    assert not answer.abstained
    assert "北部湾" in answer.text
    assert "[POL-CLOS-015 §一、休渔海域]" in answer.text
    assert answer.reason == "slot_compose"


def test_slot_gap_when_evidence_is_unrelated() -> None:
    hits = [_hit("POL-X", "第一条", "渔船应当依法办理登记手续。")]
    answer = answer_with_slots("北部湾的休渔时间是不是5月1日12时？", _Retriever(hits))
    assert answer.abstained
    assert answer.reason == "slot_gap"
    assert "缺口" in answer.text


def test_same_clause_different_slots_get_different_answers() -> None:
    hits = [_hit("POL-GEAR-016", "二、主要内容", "拖网主捕种类为鳀鱼，张网主捕种类为毛虾。")]
    first = answer_with_slots("我刺网主捕鲳鱼，网目最小要多少？", _Retriever(hits))
    second = answer_with_slots("拖网主捕虾，网囊网目最小多少？", _Retriever(hits))
    assert first.text != second.text


def test_number_with_unit_is_kept_in_gap_text() -> None:
    slot = split_slots("我这条150吨的船，最少配几个职务船员？")[0]
    answer = answer_slot(
        slot, _Retriever([_hit("POL-X", "第一条", "职务船员应当按照规定取得证书。")])
    )
    assert answer.answered and answer.partial
    text = answer_with_slots(
        "我这条150吨的船，最少配几个职务船员？",
        _Retriever([_hit("POL-X", "第一条", "职务船员应当按照规定取得证书。")]),
    )
    assert "150吨" in text.text
