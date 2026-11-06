from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from scs_fkb.models import Chunk
from scs_fkb.terms import TermError, check_terms, load_terms, validate_term


def _chunk(text: str = "违反规定的，处1000元罚款。") -> Chunk:
    return Chunk(
        chunk_id="POL-TEST-001-0000",
        doc_id="POL-TEST-001",
        source_id="POL-TEST-001",
        page=0,
        section="第五条",
        text=text,
        token_count=1,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
    )


def _data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    processed = root / "processed"
    processed.mkdir(parents=True)
    (processed / "chunks.jsonl").write_text(
        json.dumps(asdict(_chunk()), ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (processed / "manifest.json").write_text('{"index_version": "test"}', encoding="utf-8")
    return root


def _registry(tmp_path: Path) -> Path:
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
                        "hash": "a" * 64,
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def _term(**overrides):
    term = {
        "id": "TERM-001",
        "standard": "罚款",
        "variants": ["罚金"],
        "region": ["national"],
        "source": {"kind": "corpus", "doc": "POL-TEST-001", "section": "第五条"},
        "status": "approved",
    }
    term.update(overrides)
    return term


def _write(tmp_path: Path, terms: list[dict]) -> Path:
    path = tmp_path / "terms.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "terms": terms}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_valid_term_passes_check(tmp_path: Path) -> None:
    report = check_terms(
        _write(tmp_path, [_term()]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
    )
    assert report["errors"] == []
    assert report["approved"] == 1


def test_empty_variants_are_rejected() -> None:
    assert any("variants" in error for error in validate_term(_term(variants=[])))


def test_unknown_source_kind_is_rejected() -> None:
    assert any("source.kind" in error for error in validate_term(_term(source={"kind": "web"})))


def test_missing_source_doc_fails_check(tmp_path: Path) -> None:
    term = _term(source={"kind": "corpus", "doc": "POL-MISSING-001", "section": "第五条"})
    report = check_terms(
        _write(tmp_path, [term]),
        data_root=_data_root(tmp_path),
        registry_path=_registry(tmp_path),
    )
    assert any("not in the registry" in error for error in report["errors"])


def test_duplicate_standard_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(TermError, match="duplicate standard"):
        load_terms(_write(tmp_path, [_term(), _term(id="TERM-002")]))


def test_real_term_map_has_150_terms() -> None:
    root = Path(__file__).resolve().parents[1]
    terms = load_terms(root / "configs" / "terms.yaml")
    assert len(terms) == 150
    assert sum(1 for term in terms if term["status"] == "approved") == 133
    assert sum(1 for term in terms if term["status"] == "draft") == 17
    assert all(term["variants"] for term in terms)
    assert all(term["source"].get("doc") or term["source"].get("note") for term in terms)
