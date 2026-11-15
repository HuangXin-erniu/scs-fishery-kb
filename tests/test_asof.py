from __future__ import annotations

import pytest

from scs_fkb.answer_v3.channels import ChannelBook
from scs_fkb.answer_v3.compose import compose
from scs_fkb.answer_v3.select import Clause

REGISTRY = {
    "POL-LAW-009": {
        "source_class": "normative",
        "title_zh": "中华人民共和国渔业法",
        "provenance": {"document_no": "主席令第七十号"},
        "effective": {"from": "2021-07-15"},
    },
    "POL-OTHER": {
        "source_class": "normative",
        "title_zh": "渔港管理条例",
        "provenance": {"document_no": "国务院令第某号"},
        "effective": {"from": "2010-01-01"},
    },
}


@pytest.fixture(autouse=True)
def _no_rerank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCS_FKB_SUMMARY_RERANK", "off")
    monkeypatch.setenv("SCS_FKB_SUMMARY_SELECT", "on")


def test_version_line_follows_the_conclusion_document():
    """The answer cites many documents; the version note must follow the answer."""
    clause = Clause(
        text="情节严重的，并处二十万元以上二百万元以下的罚款，可以没收船舶。",
        doc_id="POL-LAW-009",
        section="第七十八条",
        rank=0,
        source_class="normative",
    )
    contract = compose(
        "船和网能不能没收？",
        clause.rendered(),
        doc_ids=["POL-OTHER", "POL-LAW-009"],
        registry=REGISTRY,
        channels=ChannelBook.load(),
        clauses=(clause,),
    )
    assert contract.as_of is not None
    assert "主席令第七十号" in contract.as_of.declared
    assert "国务院令" not in contract.as_of.declared
