from __future__ import annotations

from pathlib import Path

from scs_fkb.answer_v3 import ChannelBook, compose
from scs_fkb.answer_v3.asof import detect
from scs_fkb.answer_v3.numbers import extract, is_numeric_question
from scs_fkb.answer_v3.scope import out_of_scope

ROOT = Path(__file__).resolve().parents[1]

REGISTRY = {
    "POL-CLOS-015": {
        "title_zh": "农业农村部关于调整海洋伏季休渔制度的通告",
        "year": 2023,
        "provenance": {"document_no": "", "published_at": "2023-03-13"},
        "effective": {"from": "2023-05-01"},
    },
    "POL-STD-010": {
        "title_zh": "渔业捕捞许可管理规定",
        "year": 2022,
        "provenance": {"document_no": "农业农村部令2018年第1号", "published_at": "2022-01-07"},
        "effective": {"from": "2022-01-07"},
    },
}

EVIDENCE = (
    "（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。 "
    "[POL-CLOS-015 §三、休渔时间]"
)


def books() -> ChannelBook:
    return ChannelBook.load(ROOT / "configs" / "answer-channels.yaml")


def test_scope_detection() -> None:
    assert out_of_scope("西沙群岛现在能不能去捕鱼？")[0] is True
    assert out_of_scope("北部湾休渔什么时候开始？")[0] is False


def test_answerable_contract_is_conclusion_first() -> None:
    contract = compose(
        "今年休渔是什么时候？",
        EVIDENCE,
        doc_ids=["POL-CLOS-015"],
        registry=REGISTRY,
        channels=books(),
    )
    assert contract.answerability == "answerable"
    assert contract.conclusion.startswith("（三）北纬26度30分")
    assert contract.body.startswith("结论：")
    assert "依据摘录：" in contract.body
    assert contract.as_of is not None
    assert "2023年版" in contract.as_of.declared
    assert contract.gap == ()


def test_numeric_question_without_number_is_partial() -> None:
    contract = compose(
        "拖网的最小网目尺寸南海是多少？",
        "网目测量按扁平楔形网目内径测量仪进行。 [POL-GEAR-016 §三、测量办法]",
        doc_ids=["POL-GEAR-016"],
        registry={},
        channels=books(),
    )
    assert contract.answerability == "partial"
    assert any("数值" in item for item in contract.gap)
    assert contract.channel


def test_numeric_question_with_number_states_basis() -> None:
    contract = compose(
        "南海带鱼最小可捕规格是多少毫米？",
        "南海带鱼肛长不得小于230毫米，按重量计算幼鱼比例。 [POL-MIN-091 §第二条]",
        doc_ids=["POL-MIN-091"],
        registry={},
        channels=books(),
    )
    assert contract.answerability == "answerable"
    assert any(item.value == "230" and item.unit == "毫米" for item in contract.numbers)
    assert "230毫米" in contract.body


def test_out_of_scope_abstains_with_channel() -> None:
    contract = compose(
        "西沙群岛现在能不能去捕鱼？",
        "",
        doc_ids=[],
        registry={},
        channels=books(),
    )
    assert contract.answerability == "abstain"
    assert contract.channel
    assert "超出" in contract.gap[0]
    assert "结论：无法" in contract.body


def test_no_evidence_abstains_with_default_channel() -> None:
    contract = compose("误捕海龟怎么办？", "", doc_ids=[], registry={}, channels=books())
    assert contract.answerability == "abstain"
    assert [item.name for item in contract.channel]
    body_numbers = [ch for ch in contract.body if ch.isdigit()]
    assert not body_numbers


def test_asof_is_none_without_time_cue() -> None:
    contract = compose(
        "休渔海域包括哪些？",
        EVIDENCE,
        doc_ids=["POL-CLOS-015"],
        registry=REGISTRY,
        channels=books(),
    )
    assert contract.as_of is None


def test_asof_uses_document_number_when_available() -> None:
    note = detect(
        "现在捕捞许可证有效期几年？",
        ["POL-STD-010"],
        REGISTRY,
    )
    assert note is not None
    assert "农业农村部令2018年第1号" in note.declared


def test_channel_rules_pick_local_rule() -> None:
    book = books()
    gap, channels = book.resolve("本省休渔期停泊有什么地方规定？")
    assert "属地" in gap or "地方" in gap
    assert channels


def test_numeric_helpers() -> None:
    assert is_numeric_question("最小网目尺寸是多少？")
    assert not is_numeric_question("休渔期是什么时候？")
    anchors = extract("溶解氧不得低于6毫克，南海海区按年度值执行。")
    assert anchors and anchors[0].value == "6"
