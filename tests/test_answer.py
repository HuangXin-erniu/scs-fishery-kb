from __future__ import annotations

from scs_fkb.answer import answer_question
from scs_fkb.models import Chunk, SearchHit
from scs_fkb.text import tokenize


def _hit(
    section: str, text: str, score: float, page: int = 1, doc_id: str = "TEST-001"
) -> SearchHit:
    chunk = Chunk(
        chunk_id=section,
        doc_id=doc_id,
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


def test_province_question_answers_from_province_evidence() -> None:
    province = _hit(
        "一、休渔时间",
        "2026年5月1日12时至8月16日12时，共三个半月。",
        9.0,
        doc_id="POL-HN-059",
    )
    answer = answer_question(
        "海南省2026年休渔时间和海域是什么？",
        [],
        min_matched=0,
        extra_hits=[province],
    )
    assert answer.abstained is False
    assert answer.reason == "jurisdiction_evidence"
    assert answer.text.startswith("2026年5月1日12时")
    assert "POL-HN-059" in answer.text


def test_province_lead_precedes_national_evidence() -> None:
    national = _hit(
        "三、休渔时间",
        "（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。",
        9.0,
        doc_id="POL-CLOS-015",
    )
    province = _hit(
        "一、休渔时间",
        "2026年5月1日12时至8月16日12时，共三个半月。",
        8.0,
        doc_id="POL-HN-059",
    )
    answer = answer_question(
        "海南省2026年休渔时间和海域是什么？",
        [national],
        min_matched=1,
        extra_hits=[province],
    )
    assert answer.text.splitlines()[0].startswith("2026年5月1日12时")
    assert "POL-HN-059" in answer.text.splitlines()[0]


def test_province_penalty_question_leads_with_penalty_sentence() -> None:
    province = _hit(
        "四、休渔管理要求",
        "广东省管辖的北纬12度至闽粤海域交界线的南海海域。\n"
        "如有违反海洋伏季休渔规定的，由相关部门依法依规查处，构成犯罪的追究刑事责任。",
        9.0,
        doc_id="POL-GD-061",
    )
    answer = answer_question(
        "休渔期违规出海在广东有什么后果？",
        [],
        min_matched=0,
        extra_hits=[province],
    )
    assert "查处" in answer.text
    assert "POL-GD-061" in answer.text


def test_non_province_question_ignores_extra_hits() -> None:
    province = _hit(
        "一、休渔时间",
        "2026年5月1日12时至8月16日12时。",
        9.0,
        doc_id="POL-HN-059",
    )
    answer = answer_question(
        "南海区伏季休渔的起止日期是什么？",
        [IMPLEMENTATION, RANGES],
        min_matched=1,
        extra_hits=[province],
    )
    assert "POL-HN-059" not in answer.text
    assert "POL-CLOS-015" not in answer.text or "渤海" in answer.text or "南海" in answer.text
