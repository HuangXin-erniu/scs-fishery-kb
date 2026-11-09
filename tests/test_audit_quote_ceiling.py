from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "audit_quote_ceiling", ROOT / "scripts" / "audit_quote_ceiling.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hit(doc_id: str, text: str, section: str = "") -> SimpleNamespace:
    return SimpleNamespace(chunk=SimpleNamespace(doc_id=doc_id, text=text, section=section))


def test_term_rank_section_requires_all_terms_in_one_chunk():
    module = _module()
    hits = [_hit("A", "休渔时间从五月开始"), _hit("B", "作业类型包括拖网和围网")]
    assert module._section_rank(["休渔时间", "五月"], hits) == 0
    assert module._section_rank(["休渔时间", "围网"], hits) is None


def test_term_rank_document_allows_terms_across_chunks_of_one_document():
    module = _module()
    hits = [_hit("A", "休渔时间从五月开始"), _hit("B", "另一份文件"), _hit("A", "围网作业也受限")]
    assert module._document_rank(["休渔时间", "围网"], hits) == 2


def test_rule_rank_matches_normalized_text():
    module = _module()
    hits = [_hit("A", "罚款二千元"), _hit("B", "罚款三千元")]
    assert module._rule_rank("罚款[一二三四五]千元", hits) == 0


def test_doc_rank_keeps_first_occurrence():
    module = _module()
    hits = [_hit("A", "x"), _hit("B", "y"), _hit("A", "z")]
    assert module._doc_rank(hits, {"A", "B"}) == {"A": 0, "B": 1}


def test_expected_docs_filters_unregistered_and_records_unindexed():
    module = _module()
    docmap = SimpleNamespace(
        entries={
            "SCS-1": SimpleNamespace(docs=("DOC-1",), covers="full"),
            "SCS-2": SimpleNamespace(docs=("DOC-2",), covers="missing"),
            "SCS-3": SimpleNamespace(docs=("DOC-3",), covers="partial"),
        }
    )
    row = {"scs_doc_ids": ["SCS-1", "SCS-2", "SCS-3", "未登记"]}
    docs, unindexed, scs_ids = module._expected_docs(row, docmap, {"DOC-1"})
    assert docs == {"DOC-1", "DOC-3"}
    assert unindexed == {"DOC-3"}
    assert scs_ids == ["SCS-1", "SCS-3"]


def test_ceiling_counts_points_before_k():
    module = _module()
    assert module._ceiling([0, 4, 29, 30, None], 30) == 3
    assert module._ceiling([0, 4, 29, 30, None], 5) == 2


def test_location_rank_accepts_topic_section_and_rejects_unrelated():
    module = _module()
    row = {"citation_requirement": "SCS-1｜休渔时间"}
    hits = [_hit("DOC-1", "三、休渔时间：五月一日十二时起", section="三、休渔时间")]
    rank, source = module._location_rank(hits, {"DOC-1"}, row, [])
    assert rank == 0
    assert source in {"tokens", "lcs"}
    misses = [_hit("DOC-1", "第二条 许可证有效期", section="第二条")]
    assert module._location_rank(misses, {"DOC-1"}, row, [])[0] is None
