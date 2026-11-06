from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pytest
import yaml

from scs_fkb.facts import (
    FactError,
    check_facts,
    load_all,
    validate_fact,
)
from scs_fkb.models import Chunk

HASH = "a" * 64


def _chunk(text: str = "违反规定的，处1000元罚款。", section: str = "第五条") -> Chunk:
    return Chunk(
        chunk_id="POL-TEST-001-0000",
        doc_id="POL-TEST-001",
        source_id="POL-TEST-001",
        page=0,
        section=section,
        text=text,
        token_count=1,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
    )


def _data_root(tmp_path: Path, chunks: list[Chunk] | None = None) -> Path:
    root = tmp_path / "data"
    processed = root / "processed"
    processed.mkdir(parents=True)
    rows = [asdict(chunk) for chunk in (chunks or [_chunk()])]
    (processed / "chunks.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    (processed / "manifest.json").write_text('{"index_version": "test"}', encoding="utf-8")
    return root


def _registry(tmp_path: Path, *, hash_value: str = HASH) -> Path:
    path = tmp_path / "corpus.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "sources": [
                    {
                        "id": "POL-TEST-001",
                        "level": "national",
                        "authority_tier": "A",
                        "source_class": "normative",
                        "license": "public",
                        "sensitivity": "public",
                        "status": "acquired",
                        "currency": {
                            "as_of": "2026-11-03",
                            "basis": "publication",
                            "review_due": "2026-12-03",
                            "cadence": "monthly",
                        },
                        "retrieval": {
                            "channel": "collection",
                            "parseable": True,
                            "note": "test",
                        },
                        "lifecycle": "active",
                        "hash": hash_value,
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def _fact(**overrides):
    fact = {
        "id": "FACT-POLICY-001",
        "kind": "atomic",
        "topic": "policy",
        "question_class": "penalty",
        "subject": "测试",
        "predicate": "罚款",
        "value": "1000元",
        "unit": "CNY",
        "qualifiers": {},
        "jurisdiction": "national",
        "effective": {"from": "2026-01-01", "to": None},
        "evidence": "处1000元罚款",
        "source": {"doc": "POL-TEST-001", "section": "第五条", "sha256": HASH},
        "status": "approved",
        "confidence": "high",
        "as_of": "2026-11-04",
        "review_due": "2026-12-03",
        "supersedes": None,
    }
    fact.update(overrides)
    return fact


def _write(tmp_path: Path, facts: list[dict]) -> Path:
    path = tmp_path / "facts" / "policy.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "topic": "policy", "facts": facts}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    return path.parent


def test_valid_fact_passes_check(tmp_path: Path) -> None:
    report = check_facts(
        _write(tmp_path, [_fact()]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
        today=date(2026, 11, 4),
    )
    assert report["errors"] == []
    assert report["approved"] == 1


def test_evidence_must_be_verbatim(tmp_path: Path) -> None:
    report = check_facts(
        _write(tmp_path, [_fact(evidence="处9万元罚款")]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
        today=date(2026, 11, 4),
    )
    assert any("verbatim substring" in error for error in report["errors"])


def test_source_hash_must_match_registry(tmp_path: Path) -> None:
    report = check_facts(
        _write(tmp_path, [_fact()]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path, hash_value="b" * 64),
        today=date(2026, 11, 4),
    )
    assert any("source hash" in error for error in report["errors"])


def test_conflicting_facts_are_reported(tmp_path: Path) -> None:
    first = _fact()
    second = _fact(id="FACT-POLICY-002", value="2000元", evidence="处1000元罚款")
    report = check_facts(
        _write(tmp_path, [first, second]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
        today=date(2026, 11, 4),
    )
    assert report["conflicts"]


def test_supersedes_resolves_conflict(tmp_path: Path) -> None:
    first = _fact()
    second = _fact(
        id="FACT-POLICY-002",
        value="2000元",
        evidence="处1000元罚款",
        supersedes="FACT-POLICY-001",
    )
    report = check_facts(
        _write(tmp_path, [first, second]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
        today=date(2026, 11, 4),
    )
    assert report["conflicts"] == []


def test_expired_fact_is_reported(tmp_path: Path) -> None:
    report = check_facts(
        _write(tmp_path, [_fact(review_due="2026-01-01", as_of="2025-12-01")]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
        today=date(2026, 11, 4),
    )
    assert [row["id"] for row in report["expired"]] == ["FACT-POLICY-001"]


def test_effective_dates_cannot_invert() -> None:
    errors = validate_fact(_fact(effective={"from": "2026-12-01", "to": "2026-01-01"}))
    assert any("effective.to is before" in error for error in errors)


def test_unknown_question_class_is_rejected() -> None:
    errors = validate_fact(_fact(question_class="rumour"))
    assert any("question_class" in error for error in errors)


def test_load_all_reads_yaml(tmp_path: Path) -> None:
    _write(tmp_path, [_fact()])
    facts = load_all(tmp_path / "facts")
    assert [fact["id"] for fact in facts] == ["FACT-POLICY-001"]


def test_real_fact_layer_has_200_facts() -> None:
    root = Path(__file__).resolve().parents[1]
    facts = load_all(root / "configs" / "facts")
    assert len(facts) == 200
    assert sum(1 for fact in facts if fact["kind"] == "atomic") == 20
    assert sum(1 for fact in facts if fact["kind"] == "provision") == 180
    assert sum(1 for fact in facts if fact["status"] == "approved") == 100
    assert sum(1 for fact in facts if fact["status"] == "draft") == 100
    for fact in facts:
        assert fact["evidence"]
        assert fact["source"]["sha256"]


def test_fact_layer_does_not_read_eval() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("facts.py", "terms.py", "faq.py"):
        text = (root / "src" / "scs_fkb" / name).read_text(encoding="utf-8")
        assert "eval.yaml" not in text
        assert "configs/eval" not in text


def test_malformed_fact_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "facts" / "policy.yaml"
    path.parent.mkdir()
    path.write_text("schema_version: 1\nfacts: [{}]\n", encoding="utf-8")
    with pytest.raises(FactError):
        load_all(tmp_path / "facts")
