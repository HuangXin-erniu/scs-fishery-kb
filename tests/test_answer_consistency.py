from __future__ import annotations

from scs_fkb.audit.consistency import check


def test_duplicate_answers_are_hard_failures() -> None:
    rows = [
        {"id": "A", "question": "电鱼怎么罚", "visible_answer": "没收工具并罚款。" * 10},
        {"id": "B", "question": "禁渔期电鱼怎么定性", "visible_answer": "没收工具并罚款。" * 10},
    ]
    problems = check(rows)
    assert any(kind == "DUP_ANSWER" for kind, _, _ in problems)


def test_same_answer_for_refusals_is_not_duplicate() -> None:
    rows = [
        {"id": "A", "question": "甲", "visible_answer": "证据不足：未能生成可核验的完整答复。"},
        {"id": "B", "question": "乙", "visible_answer": "证据不足：未能生成可核验的完整答复。"},
    ]
    assert not any(kind == "DUP_ANSWER" for kind, _, _ in check(rows))
