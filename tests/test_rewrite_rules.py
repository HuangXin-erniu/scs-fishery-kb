from __future__ import annotations

from scs_fkb.retrieve_v2.rewrite_rules import rewrite_question


def test_rewrite_adds_domain_terms_and_keeps_original() -> None:
    rewritten = rewrite_question("误捕白海豚死亡，执法怎么处置？")
    assert rewritten.startswith("误捕白海豚死亡，执法怎么处置？")
    assert "野生" in rewritten
    assert "报告" in rewritten


def test_rewrite_returns_original_without_rule_match() -> None:
    question = "今天天气怎么样？"
    assert rewrite_question(question) == question


def test_night_navigation_rewrite() -> None:
    rewritten = rewrite_question("珠江口船多，晚上过伶仃洋要注意什么？")
    assert "瞭望" in rewritten
    assert "避碰" in rewritten


def test_question_type_rewrites() -> None:
    assert "有效期" in rewrite_question("许可证几年到期？")
    assert "罚款" in rewrite_question("无证捕捞罚多少？")
    assert "听证" in rewrite_question("没收渔船的程序是什么？")
