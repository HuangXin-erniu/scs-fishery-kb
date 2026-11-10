from __future__ import annotations

import json

import pytest

from scs_fkb.answer_v3.short_arm import MAX_ANSWER_CHARS, answer_with_short
from scs_fkb.llm import LLMError
from scs_fkb.models import Chunk, SearchHit


class FakeConfig:
    model = "fake-model"


class FakeClient:
    def __init__(self, replies: list[dict]) -> None:
        self.config = FakeConfig()
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages, *, temperature=0.0, max_tokens=1200):  # noqa: ANN001
        self.calls += 1
        return json.dumps(self.replies.pop(0), ensure_ascii=False)


def _hit(text: str = "南海区休渔时间为5月1日12时至8月16日12时。") -> SearchHit:
    chunk = Chunk(
        chunk_id="CH-1",
        doc_id="POL-CLOS-015",
        source_id="POL-CLOS-015",
        page=1,
        section="三、休渔时间",
        text=text,
        token_count=10,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_short_answer_renders_cited_text() -> None:
    client = FakeClient(
        [
            {
                "conclusion": "南海区休渔时间为5月1日12时至8月16日12时 [POL-CLOS-015 §三]",
                "basis": [],
                "deadline": ("8月16日12时后开渔 [POL-CLOS-015 §三]"),
                "documents": ["捕捞许可证"],
                "caveat": "",
            }
        ]
    )
    answer = answer_with_short("休渔时间？", [_hit()], client, None)
    assert not answer.abstained
    assert "[POL-CLOS-015 §三]" in answer.text
    assert "期限：8月16日12时后开渔" in answer.text
    assert answer.citations
    assert len(answer.text) <= MAX_ANSWER_CHARS


def test_short_answer_rejects_an_ungrounded_number_after_repair() -> None:
    client = FakeClient(
        [
            {
                "conclusion": "休渔到9月30日 [POL-CLOS-015 §三、休渔时间]",
                "basis": [],
                "deadline": "",
                "documents": [],
                "caveat": "",
            },
            {
                "conclusion": "休渔到9月30日 [POL-CLOS-015 §三、休渔时间]",
                "basis": [],
                "deadline": "",
                "documents": [],
                "caveat": "",
            },
        ]
    )
    with pytest.raises(LLMError, match="short_invalid"):
        answer_with_short("休渔时间？", [_hit()], client, None)


def test_short_answer_rejects_a_missing_citation() -> None:
    client = FakeClient(
        [
            {
                "conclusion": "南海区休渔时间很长。",
                "basis": [],
                "deadline": "",
                "documents": [],
                "caveat": "",
            },
            {
                "conclusion": "南海区休渔时间很长。",
                "basis": [],
                "deadline": "",
                "documents": [],
                "caveat": "",
            },
        ]
    )
    with pytest.raises(LLMError, match="short_invalid"):
        answer_with_short("休渔时间？", [_hit()], client, None)
