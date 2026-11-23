from types import SimpleNamespace

from scs_fkb.retrieve_v2.doc_rank import rank_documents


def _hit(doc_id, section, score, text="第六条 处罚"):
    return SimpleNamespace(
        chunk=SimpleNamespace(doc_id=doc_id, section=section, text=text), score=score
    )


def test_gold_document_can_rank_first():
    hits = [
        _hit("OTHER", "第一条", 1.0, "无关内容"),
        _hit("GOLD", "第六条", 0.8, "第六条 罚款 三十万元"),
    ]
    ranked = rank_documents(
        "第六条 罚款多少", hits, {"GOLD": {"title": "处罚规定"}}, weights=(0.0, 0.0, 1.0, 0.0)
    )
    assert ranked[0][0] == "GOLD"


def test_empty_hits():
    assert rank_documents("问题", []) == []
