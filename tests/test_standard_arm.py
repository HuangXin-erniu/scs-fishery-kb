from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scs_fkb.answer_v3.evidence import build_evidence_pack
from scs_fkb.answer_v3.standard_arm import answer_with_standard
from scs_fkb.models import Chunk, SearchHit

CITATION = "[POL-CLOS-015 §三、休渔时间]"


def _pack():
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
        source_id="POL-CLOS-015",
        page=3,
        section="三、休渔时间",
        text="北纬26度30分至北纬12度的东海和南海海域，休渔时间为5月1日12时至8月16日12时。",
        token_count=30,
        char_start=0,
        char_end=50,
        sensitivity="public",
        authority_tier="A",
        level="national",
    )
    return build_evidence_pack([SearchHit(chunk=chunk, score=1.0)])


class FakeClient:
    def __init__(self, replies: list[dict]) -> None:
        self.replies = list(replies)
        self.calls = 0
        self.config = SimpleNamespace(model="fake-standard")

    def chat(self, messages, **kwargs) -> str:
        self.calls += 1
        if not self.replies:
            raise AssertionError("unexpected model call")
        return json.dumps(self.replies.pop(0), ensure_ascii=False)


@pytest.fixture(autouse=True)
def _selfcheck_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCS_FKB_STANDARD_SELFCHECK", "off")


def test_standard_answer_is_cited_and_structured() -> None:
    client = FakeClient(
        [
            {
                "answerability": "answerable",
                "conclusion": f"南海区伏季休渔时间为5月1日12时至8月16日12时。{CITATION}",
                "applicability": f"南海区（北纬26度30分至12度）。{CITATION}",
                "steps": [],
                "documents": [],
                "deadline": "",
                "basis": [CITATION],
                "caveat": "具体年度以当年通告为准。",
                "soft_gap": [],
                "missing_slots": [],
                "citations": [CITATION],
            }
        ]
    )
    result = answer_with_standard("南海区伏季休渔从什么时候开始？", _pack(), client)
    assert result.answer.abstained is False
    assert result.answer.citations
    assert result.answer.citations[0].doc_id == "POL-CLOS-015"
    assert result.confidence > 0.5
    assert result.contract_fields["answerability"] == "answerable"
    assert "5月1日12时" in result.answer.text
    assert "适用：" in result.answer.text


def test_standard_refuses_when_answerability_is_refuse() -> None:
    client = FakeClient(
        [
            {
                "answerability": "refuse",
                "conclusion": "",
                "missing_slots": ["没有可引用的条款"],
            }
        ]
    )
    result = answer_with_standard("不存在的海洋生物是什么？", _pack(), client)
    assert result.answer.abstained is True
    assert result.answer.reason == "standard_refuse"
    assert result.contract_fields["answerability"] == "abstain"


def test_standard_clarifies_when_slots_missing() -> None:
    client = FakeClient(
        [
            {
                "answerability": "clarify",
                "conclusion": "",
                "missing_slots": ["省份", "年份"],
            }
        ]
    )
    result = answer_with_standard("今年休渔什么时候开始？", _pack(), client)
    assert result.answer.abstained is True
    assert result.answer.reason == "clarify"
    assert result.missing == ("省份", "年份")


def test_standard_abstains_on_invalid_citation() -> None:
    client = FakeClient(
        [
            {
                "answerability": "answerable",
                "conclusion": "休渔时间为5月1日12时。[POL-LAW-009 §不存在的章节]",
                "applicability": "",
                "steps": [],
                "documents": [],
                "deadline": "",
                "basis": [],
                "caveat": "",
                "soft_gap": [],
                "missing_slots": [],
                "citations": ["[POL-LAW-009 §不存在的章节]"],
            }
        ]
    )
    result = answer_with_standard("休渔时间？", _pack(), client)
    assert result.answer.abstained is True
    assert result.answer.reason == "standard_citation_invalid"


def test_standard_falls_back_to_extractive_evidence_when_no_citation() -> None:
    client = FakeClient(
        [
            {
                "answerability": "answerable",
                "conclusion": "休渔时间为5月1日12时。",
                "applicability": "",
                "steps": [],
                "documents": [],
                "deadline": "",
                "basis": [],
                "caveat": "",
                "soft_gap": [],
                "missing_slots": [],
                "citations": [],
            },
            {"conclusion": "休渔时间为5月1日12时。"},
        ]
    )
    result = answer_with_standard("休渔时间？", _pack(), client)
    assert result.answer.abstained is False
    assert "[" in result.answer.text


def test_empty_pack_abstains_without_model_call() -> None:
    client = FakeClient([])
    result = answer_with_standard("休渔时间？", build_evidence_pack([]), client)
    assert result.answer.abstained is True
    assert result.answer.reason == "no_evidence"
    assert client.calls == 0
