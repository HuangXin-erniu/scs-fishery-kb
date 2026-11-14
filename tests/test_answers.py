from __future__ import annotations

from scs_fkb.knowledge_v2.answers import (
    build_from_faq,
    load_answers,
    search_answers,
    validate_answers,
)

FAQ = {
    "id": "FAQ-001",
    "question": "南海伏季休渔什么时候开始？",
    "variants": ["休渔期是哪几个月"],
    "persona": "captain",
    "answer": "5月1日12时至8月16日12时",
    "status": "approved",
    "citations": [
        {
            "doc": "POL-CLOS-015",
            "section": "三、休渔时间",
            "quote": "北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。",
        }
    ],
}


def test_build_from_faq_creates_approved_answer() -> None:
    answers = build_from_faq([FAQ])
    assert len(answers) == 1
    entry = answers[0]
    assert entry["id"] == "ANS-001"
    assert entry["status"] == "approved"
    assert entry["evidence"][0]["doc"] == "POL-CLOS-015"
    assert validate_answers(answers, registry={"POL-CLOS-015": {}}) == []


def test_answer_without_evidence_is_rejected() -> None:
    answers = build_from_faq([FAQ])
    answers[0]["evidence"] = []
    errors = validate_answers(answers, registry={"POL-CLOS-015": {}})
    assert any("evidence must be a non-empty list" in error for error in errors)


def test_answer_with_unknown_doc_is_rejected() -> None:
    answers = build_from_faq([FAQ])
    answers[0]["evidence"][0]["doc"] = "POL-MISSING-999"
    errors = validate_answers(answers, registry={"POL-CLOS-015": {}})
    assert any("is not registered" in error for error in errors)


def test_search_answers_matches_question_or_alias() -> None:
    answers = build_from_faq([FAQ])
    assert search_answers(answers, "伏季休渔什么时候开始")["id"] == "ANS-001"
    assert search_answers(answers, "休渔期是哪几个月")["id"] == "ANS-001"
    assert search_answers(answers, "完全不相关的问题") is None


def test_live_answers_validate() -> None:
    from scs_fkb.registry import load_registry

    answers = load_answers()
    assert answers
    assert validate_answers(answers, registry=load_registry()) == []
    assert all(entry["status"] in {"draft", "approved", "retired"} for entry in answers)
