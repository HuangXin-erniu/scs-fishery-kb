from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.claims import ClaimError, classify, load_claims
from scs_fkb.models import Chunk, SearchHit

CONFIG = Path("configs/claims.yaml")
CASES = {
    "伏季休渔的定义是什么？": ("definition", "policy"),
    "申请捕捞许可证需要提交哪些材料？": ("rule", "policy"),
    "2025年南海捕捞产量是多少？": ("quantity", "statistics"),
    "目前的伏季休渔时间是否有效？": ("status", "policy"),
    "台风预警信号分几级？": ("warning", "hazard"),
    "大黄鱼的学名和保护等级是什么？": ("identification", "species"),
    "休渔制度的修订沿革是什么？": ("history", "policy"),
}


def test_each_nature_and_domain() -> None:
    config = load_claims(CONFIG)
    for question, (nature, domain) in CASES.items():
        result = classify(question, config)
        assert result["nature"] == nature, question
        assert result["domain"] == domain, question


def test_unknown_question_falls_back() -> None:
    config = load_claims(CONFIG)
    result = classify("今天适合出门吗？", config)
    assert result["nature"] == "general"
    assert result["domain"] == "general"


def test_bad_nature_set_is_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data["natures"].pop("history")
    path = tmp_path / "claims.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ClaimError, match="natures"):
        load_claims(path)


def test_empty_keywords_are_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data["natures"]["definition"]["keywords"] = []
    path = tmp_path / "claims.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ClaimError, match="definition"):
        load_claims(path)


def _hit(kind: str, source_class: str, trust: str, review_due: str = "2026-12-03") -> SearchHit:
    text = "休渔时间 5月1日12时至8月16日12时"
    chunk = Chunk(
        chunk_id=f"{kind}-1",
        doc_id="POL-CLOS-015" if kind == "corpus" else "WEB-1",
        source_id="POL-CLOS-015" if kind == "corpus" else "WEB-1",
        page=0,
        section="三、休渔时间",
        text=text,
        token_count=8,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        kind=kind,
        source_class=source_class,
        trust=trust,
        review_due=review_due,
    )
    return SearchHit(chunk=chunk, score=1.0)


def test_select_evidence_by_trust_and_kind() -> None:
    from datetime import date

    from scs_fkb.claims import select_evidence

    config = load_claims(CONFIG)
    hits = [
        _hit("note", "reference", "standard"),
        _hit("corpus", "normative", "authoritative"),
        _hit("web", "reference", "standard"),
    ]
    result = select_evidence("目前的伏季休渔时间是否有效？", hits, config, today=date(2026, 11, 3))
    assert result["nature"] == "status"
    assert result["primary"].chunk.kind == "corpus"
    assert result["supporting"] == []


def test_select_evidence_drops_expired_status() -> None:
    from datetime import date

    from scs_fkb.claims import select_evidence

    config = load_claims(CONFIG)
    hits = [_hit("corpus", "normative", "authoritative", review_due="2026-01-01")]
    result = select_evidence("目前的伏季休渔时间是否有效？", hits, config, today=date(2026, 11, 3))
    assert result["primary"] is None


def test_general_question_uses_corpus_only() -> None:
    from datetime import date

    from scs_fkb.claims import select_evidence

    config = load_claims(CONFIG)
    hits = [_hit("web", "reference", "standard"), _hit("corpus", "normative", "authoritative")]
    result = select_evidence("今天出门合适吗？", hits, config, today=date(2026, 11, 3))
    assert result["nature"] == "general"
    assert result["primary"].chunk.kind == "corpus"
    assert result["supporting"] == []
