from __future__ import annotations

from types import SimpleNamespace

from scs_fkb.answer_v3.support import prune_unsupported, support_score
from scs_fkb.service_v2.answer import _scope_note_applies


def _item(doc: str, section: str, text: str):
    chunk = SimpleNamespace(doc_id=doc, section=section, page=0, text=text)
    return SimpleNamespace(label=f"{doc} §{section}", chunk=chunk, quote=text)


def _pack(*items):
    return SimpleNamespace(items=tuple(items))


def test_support_score_rejects_missing_number() -> None:
    assert support_score("幼鱼比例不得超过20%", "幼鱼比例不得超过30%") == 0.0


def test_supported_sentence_is_kept() -> None:
    item = _item("POL-A-001", "第一条", "渔业船舶必须经检验合格并取得证书。")
    text = "渔业船舶必须经检验合格并取得证书 [POL-A-001 §第一条]。"
    cleaned, dropped = prune_unsupported(text, _pack(item))
    assert dropped == 0
    assert cleaned == text


def test_wrong_citation_is_replaced_from_the_pack() -> None:
    wrong = _item("POL-A-001", "第二条", "渔港经营者不得拒绝船舶进港避风。")
    right = _item("POL-B-002", "第五条", "渔业船舶必须经检验合格并取得检验证书。")
    text = "渔业船舶必须经检验合格并取得检验证书 [POL-A-001 §第二条]。"
    cleaned, dropped = prune_unsupported(text, _pack(wrong, right))
    assert dropped == 0
    assert "[POL-B-002 §第五条]" in cleaned
    assert "[POL-A-001 §第二条]" not in cleaned


def test_unsupported_sentence_is_dropped_with_a_gap_line() -> None:
    item = _item("POL-A-001", "第一条", "渔业船舶必须经检验合格并取得证书。")
    text = (
        "渔业船舶必须经检验合格并取得证书 [POL-A-001 §第一条]。\n"
        "因此，所有渔船都可以免于检验 [POL-A-001 §第一条]。"
    )
    cleaned, dropped = prune_unsupported(text, _pack(item))
    assert dropped == 1
    assert "免于检验" not in cleaned
    assert "已删除" not in cleaned


def test_gap_and_caveat_lines_are_not_pruned() -> None:
    item = _item("POL-A-001", "第一条", "渔业船舶必须经检验合格并取得证书。")
    text = "缺口：未覆盖跨省迁移程序\n注意：以属地规定为准。"
    cleaned, dropped = prune_unsupported(text, _pack(item))
    assert dropped == 0
    assert cleaned == text


def test_scope_note_requires_a_term_and_question_overlap() -> None:
    note = "未按规定跟帮（组）生产，处500元以上1000元以下罚款。"
    assert not _scope_note_applies(note, "船长证分几级？", [])
    assert not _scope_note_applies(note, "船长证分几级？", ["跟帮", "编组"])
    assert _scope_note_applies(note, "跟帮生产怎么罚？", ["跟帮", "编组"])


def test_support_score_rejects_a_level_switch() -> None:
    assert (
        support_score(
            "我国分布的所有海龟均被列为国家一级重点保护野生动物",
            "我国分布的所有海龟均被列为国家二级重点保护野生动物。",
        )
        == 0.0
    )


def test_repair_citations_uses_another_chunk_of_the_same_document() -> None:
    from scs_fkb.answer_v3.support import repair_citations

    wrong = _item("POL-A-001", "第二条", "渔港经营者不得拒绝船舶进港避风。")
    right = _item("POL-A-001", "第五条", "渔业船舶必须经检验合格并取得检验证书。")
    text = "渔业船舶必须经检验合格并取得检验证书 [POL-A-001 §第二条]。"
    cleaned, repaired = repair_citations(text, [wrong.chunk, right.chunk])
    assert repaired == 1
    assert "[POL-A-001 §第五条]" in cleaned
