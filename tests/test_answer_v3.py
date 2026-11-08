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


def test_asof_declares_for_cited_policy_without_time_cue() -> None:
    from scs_fkb.answer_v3 import asof

    registry = {
        "POL-CLOS-015": {
            "source_class": "normative",
            "year": 2026,
            "provenance": {"document_no": "通告〔2026〕2号", "published_at": "2026-07-30"},
            "effective": {"from": "2026-07-30"},
            "title_zh": "关于调整海洋伏季休渔制度的通告",
        }
    }
    declared = asof.detect("拖网网囊网目最小多少？", ["POL-CLOS-015"], registry)
    assert declared is not None
    assert declared.basis == "cited_policy"
    assert "2026" in declared.declared


def test_asof_skips_non_policy_citation_without_cue() -> None:
    from scs_fkb.answer_v3 import asof

    registry = {"PAPER-105": {"source_class": "reference", "year": 2025}}
    assert asof.detect("网目怎么量？", ["PAPER-105"], registry) is None


# --- LLM composition arm (offline) ---
import json  # noqa: E402

from scs_fkb.answer_v3.llm_answer import answer_with_llm  # noqa: E402
from scs_fkb.models import Chunk, SearchHit  # noqa: E402

CITED_108 = "休渔时间为5月1日12时至8月16日12时，共108天。 [POL-CLOS-015 §三、休渔时间]"
CITED_130 = "休渔时间为5月1日12时至8月16日12时，共130天。 [POL-CLOS-015 §三、休渔时间]"


class FakeConfig:
    model = "fake-model"


class FakeClient:
    def __init__(self, replies: list[dict]) -> None:
        self.config = FakeConfig()
        self.replies = list(replies)
        self.calls: list[str] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=1200):  # noqa: ANN001
        system = messages[0]["content"]
        if "修复" in system:
            kind = "repair"
        elif "核验" in system:
            kind = "verify"
        else:
            kind = "answer"
        self.calls.append(kind)
        value = self.replies.pop(0)
        return json.dumps(value, ensure_ascii=False)


def make_hit(
    doc_id: str = "POL-CLOS-015", section: str = "三、休渔时间", text: str = ""
) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"{doc_id}-1",
        doc_id=doc_id,
        source_id="POL-CLOS",
        page=3,
        section=section,
        text=text or "休渔时间为5月1日12时至8月16日12时，共108天。",
        token_count=20,
        char_start=0,
        char_end=40,
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_valid_answer_passes_checks() -> None:
    client = FakeClient(
        [
            {
                "abstained": False,
                "answer": CITED_108,
                "reason": "ok",
            },
            {"supported": True, "reason": ""},
        ]
    )
    answer = answer_with_llm("南海休渔到几号？", [make_hit()], client, cache=None)
    assert answer.abstained is False
    assert answer.reason == "llm_compose"
    assert answer.citations and answer.citations[0].doc_id == "POL-CLOS-015"


def test_ungrounded_number_after_repair_abstains() -> None:
    client = FakeClient(
        [
            {
                "abstained": False,
                "answer": CITED_130,
                "reason": "ok",
            },
            {
                "abstained": False,
                "answer": CITED_130,
                "reason": "ok",
            },
        ]
    )
    answer = answer_with_llm("南海休渔到几号？", [make_hit()], client, cache=None)
    assert answer.abstained is True
    assert answer.reason.startswith("llm_ungrounded")
    assert client.calls == ["answer", "repair"]


def test_unsupported_answer_is_abstained() -> None:
    client = FakeClient(
        [
            {
                "abstained": False,
                "answer": CITED_108,
                "reason": "ok",
            },
            {"supported": False, "reason": "结论超出证据"},
        ]
    )
    answer = answer_with_llm("南海休渔到几号？", [make_hit()], client, cache=None)
    assert answer.abstained is True
    assert answer.reason.startswith("llm_unsupported")


def test_llm_abstain_is_passed_through() -> None:
    client = FakeClient([{"abstained": True, "answer": "", "reason": "证据没有休渔时间"}])
    answer = answer_with_llm("南海休渔到几号？", [make_hit()], client, cache=None)
    assert answer.abstained is True
    assert "llm_abstain" in answer.reason
