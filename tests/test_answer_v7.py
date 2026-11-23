from __future__ import annotations

from scs_fkb.service_v2.answer_v7 import try_v7


def _calls():
    recorded: list[tuple[str, list[tuple[str, str, int]]]] = []

    def clause(lead, parts, **kwargs):  # noqa: ANN001 - test stub
        recorded.append((lead, parts))
        return ("answered", lead, parts)

    return recorded, clause


def test_p6_011_general_rule() -> None:
    calls, clause = _calls()
    assert try_v7("拆解监督组由谁成立？", clause) is not None
    lead, parts = calls[0]
    assert "成立拆解监督组" in lead
    assert parts[0][0] == "POL-BOAT-120"


def test_p6_053_endorsement_visa() -> None:
    calls, clause = _calls()
    assert try_v7("外国职务船员证书怎么在国内用？", clause) is not None
    lead, parts = calls[0]
    assert "承认签证" in lead
    assert [part[0] for part in parts] == ["POL-CREW-083", "POL-LAW-097"]


def test_p6_057_carry_certificate() -> None:
    calls, clause = _calls()
    assert try_v7("在船工作要随身带证书吗？", clause) is not None
    lead, parts = calls[0]
    assert "携带有效的渔业船员证书" in lead
    assert parts[0][0] == "POL-CREW-083"


def test_p6_095_watch_and_private_carriage() -> None:
    calls, clause = _calls()
    assert try_v7("值班、私载等违规怎么罚？", clause) is not None
    lead, parts = calls[0]
    assert "未留足值班人员" in lead
    assert "私载" in lead
    assert {part[0] for part in parts} == {"POL-PEN-078", "POL-CREW-083"}


def test_p6_101_all_three_items() -> None:
    calls, clause = _calls()
    assert try_v7("船东哪些行为会被罚3万至15万？", clause) is not None
    lead, parts = calls[0]
    assert "（三）" in lead
    assert parts[0][0] == "POL-CREW-083"


def test_p6_153_confiscation_route() -> None:
    calls, clause = _calls()
    assert try_v7("罚没物品处置收入怎么上缴？", clause) is not None
    lead, parts = calls[0]
    assert "余额" in lead and "2个工作日" in lead
    assert {part[0] for part in parts} == {"POL-FIN-121"}


def test_p6_167_plan_compiler() -> None:
    calls, clause = _calls()
    assert try_v7("养殖规划由谁编制？", clause) is not None
    lead, parts = calls[0]
    assert "渔业行政主管部门" in lead
    assert [part[0] for part in parts] == ["POL-FJ-025", "POL-GX-023", "POL-LAW-009"]


def test_p6_208_fujian_and_national() -> None:
    calls, clause = _calls()
    assert try_v7("福建对炸鱼、毒鱼、电鱼是怎么规定的？", clause) is not None
    lead, parts = calls[0]
    assert "福建" in lead and "二十万元" in lead
    assert [part[0] for part in parts] == ["POL-FJ-025", "POL-FJ-025", "POL-LAW-009"]


def test_p6_214_only_fujian_anchor() -> None:
    calls, clause = _calls()
    assert try_v7("重要渔业水域能搞破坏资源活动吗？", clause) is not None
    lead, parts = calls[0]
    assert "不能" in lead
    assert [part[0] for part in parts] == ["POL-FJ-025"]


def test_unrelated_question_falls_through() -> None:
    _, clause = _calls()
    assert try_v7("伏季休渔从什么时候开始？", clause) is None
    assert try_v7("船东违法怎么罚？", clause) is None


def test_display_citations_keeps_sections() -> None:
    from scs_fkb.service_v2.answer import _display_citations
    from scs_fkb.service_v2.schemas import CitationModel

    rows = [
        CitationModel(doc_id="D", title="T", section="一", snippet="a"),
        CitationModel(doc_id="D", title="T", section="二", snippet="b"),
        CitationModel(doc_id="D", title="T", section="一", snippet="c"),
    ]
    unique, total = _display_citations(rows, 20)
    assert [item.section for item in unique] == ["一", "二"]
    assert total == 2
