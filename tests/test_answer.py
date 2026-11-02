from __future__ import annotations

from scs_fkb.answer import answer_question
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.text import tokenize


def _hit(section: str, text: str, score: float, page: int = 1) -> SearchHit:
    chunk = Chunk(
        chunk_id=section,
        doc_id="TEST-001",
        source_id="TEST-001",
        page=page,
        section=section,
        text=text,
        token_count=len(tokenize(text)),
        char_start=0,
        char_end=len(text),
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=score)


IMPLEMENTATION = _hit(
    "四、实施时间",
    "四、实施时间 上述调整后的休渔规定，自2023年4月15日起施行。",
    10.0,
)
RANGES = _hit(
    "三、休渔时间",
    "三、休渔时间\n"
    "（一）北纬35度以北的渤海和黄海海域为5月1日12时至9月1日12时。\n"
    "（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。",
    8.0,
)


def test_period_question_leads_with_range() -> None:
    answer = answer_question(
        "南海区伏季休渔的起止日期是什么？", [IMPLEMENTATION, RANGES], min_matched=1
    )
    assert not answer.abstained
    first = answer.text.splitlines()[0]
    assert "5月1日12时至8月16日12时" in first
    assert "三、休渔时间" in first
    assert "2023年4月15日" not in first


def test_implementation_question_keeps_implementation_lead() -> None:
    answer = answer_question("这项规定什么时候施行？", [IMPLEMENTATION, RANGES], min_matched=1)
    assert not answer.abstained
    first = answer.text.splitlines()[0]
    assert "2023年4月15日" in first


def test_question_without_time_words_keeps_top_hit() -> None:
    answer = answer_question("休渔规定包含哪些内容？", [IMPLEMENTATION, RANGES], min_matched=1)
    assert not answer.abstained
    first = answer.text.splitlines()[0]
    assert "2023年4月15日" in first


def test_no_range_falls_back_to_previous_selection() -> None:
    only_reports = _hit("二、休渔作业类型", "二、休渔作业类型 除钓具外的所有作业类型。", 9.0)
    answer = answer_question("休渔的起止日期是什么？", [only_reports], min_matched=1)
    assert not answer.abstained
    assert "休渔作业类型" in answer.text
