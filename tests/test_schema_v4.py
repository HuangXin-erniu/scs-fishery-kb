from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.registry import RegistryError, load_registry

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def _entry(**overrides):
    entry = {
        "id": "POL-TEST-001",
        "title": "test",
        "status": "acquired",
        "level": "national",
        "authority_tier": "A",
        "source_class": "normative",
        "currency": {
            "as_of": "2026-11-03",
            "basis": "publication",
            "review_due": "2026-12-03",
            "cadence": "monthly",
        },
        "retrieval": {"channel": "main", "parseable": True, "note": "registered"},
        "lifecycle": "active",
        "license": "public",
        "sensitivity": "public",
        "hash": HASH,
        "location": "raw/POL-TEST-001/test.html",
    }
    entry.update(overrides)
    return entry


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "corpus.yaml"
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "source_record_schema": 4, "sources": entries},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def test_live_register_loads_all_sources_as_v5() -> None:
    registry = load_registry(ROOT / "configs" / "corpus.yaml")
    assert len(registry) == 126
    provisional = [
        source for source in registry.values() if source["ingest"]["tier"] == "provisional"
    ]
    assert len(provisional) == 1
    for source in registry.values():
        assert source["source_record_schema"] == 5
        assert source["provenance"]["sha256"] == source["hash"]
        assert source["provenance"]["snapshot_path"] == source["location"]
        assert set(source["effective"]) == {"from", "to"}
        assert {
            "text_layer",
            "anchors",
            "tables",
            "ocr",
            "quarantine_reason",
            "text_coverage",
            "anchor_coverage",
            "table_count",
            "ocr_confidence",
        } <= set(source["quality"])
        assert source["ingest"]["tier"] in {"canonical", "provisional"}
        assert 0 <= int(source["authority"]["score"]) <= 5
        assert "practical" in source
        assert isinstance(source["currency"].get("ttl_days"), int)


def test_v3_fixture_gets_derived_v5_defaults(tmp_path: Path) -> None:
    registry = load_registry(_write(tmp_path, [_entry()]))
    source = registry["POL-TEST-001"]
    assert source["source_record_schema"] == 5
    assert source["provenance"]["sha256"] == HASH
    assert source["provenance"]["snapshot_path"] == "raw/POL-TEST-001/test.html"
    assert source["effective"] == {"from": None, "to": None}
    assert source["quality"]["anchors"] is None
    assert source["license_note"] is None
    assert source["authority"]["score"] == 5
    assert source["ingest"]["tier"] == "canonical"
    assert source["practical"] == {
        "domain": "",
        "personas": [],
        "task_tags": [],
        "seasonal": False,
    }
    assert source["currency"]["ttl_days"] == 30
    assert source["license_evidence"]["checked_at"] == "2026-11-03"


def test_tier_d_non_official_is_accepted(tmp_path: Path) -> None:
    entry = _entry(
        level="non_official",
        authority_tier="D",
        source_class="reference",
        retrieval={"channel": "local", "parseable": True, "note": "local expert text"},
    )
    registry = load_registry(_write(tmp_path, [entry]))
    assert registry["POL-TEST-001"]["authority_tier"] == "D"


def test_tier_d_requires_non_official(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="authority_tier D requires level non_official"):
        load_registry(_write(tmp_path, [_entry(authority_tier="D")]))


def test_non_official_requires_tier_d(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="level non_official requires authority_tier D"):
        load_registry(_write(tmp_path, [_entry(level="non_official")]))


def test_tier_c_requires_municipal(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="authority_tier C requires level municipal"):
        load_registry(_write(tmp_path, [_entry(authority_tier="C")]))


def test_tier_a_cannot_be_non_official(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="cannot be non_official"):
        load_registry(_write(tmp_path, [_entry(level="non_official", authority_tier="A")]))


def test_licensed_requires_note(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="license licensed requires license_note"):
        load_registry(_write(tmp_path, [_entry(license="licensed")]))


def test_licensed_with_note_is_accepted(tmp_path: Path) -> None:
    entry = _entry(license="licensed", license_note="Authorization 2026-001")
    registry = load_registry(_write(tmp_path, [entry]))
    assert registry["POL-TEST-001"]["license"] == "licensed"


def test_explicit_provenance_is_accepted(tmp_path: Path) -> None:
    entry = _entry(
        provenance={
            "url": "https://example.org/document",
            "document_no": "农渔发〔2026〕1号",
            "published_at": "2026-01-01",
            "retrieved_at": "2026-11-03",
            "sha256": HASH,
            "bytes": 1024,
            "mime": "text/html",
            "snapshot_path": "snapshots/POL-TEST-001/" + HASH,
        }
    )
    registry = load_registry(_write(tmp_path, [entry]))
    assert registry["POL-TEST-001"]["provenance"]["bytes"] == 1024


def test_provenance_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    entry = _entry(provenance={"sha256": "b" * 64, "snapshot_path": "x"})
    with pytest.raises(RegistryError, match="provenance.sha256 does not match hash"):
        load_registry(_write(tmp_path, [entry]))


def test_provenance_absolute_path_is_rejected(tmp_path: Path) -> None:
    entry = _entry(provenance={"sha256": HASH, "snapshot_path": "/tmp/private/file"})
    with pytest.raises(RegistryError, match="snapshot_path must stay under the data root"):
        load_registry(_write(tmp_path, [entry]))


def test_provenance_parent_path_is_rejected(tmp_path: Path) -> None:
    entry = _entry(provenance={"sha256": HASH, "snapshot_path": "../secret"})
    with pytest.raises(RegistryError, match="snapshot_path must stay under the data root"):
        load_registry(_write(tmp_path, [entry]))


def test_provenance_non_http_url_is_rejected(tmp_path: Path) -> None:
    entry = _entry(provenance={"sha256": HASH, "url": "ftp://example.org/file"})
    with pytest.raises(RegistryError, match="provenance.url must start with http"):
        load_registry(_write(tmp_path, [entry]))


def test_provenance_invalid_date_is_rejected(tmp_path: Path) -> None:
    entry = _entry(provenance={"sha256": HASH, "published_at": "03/11/2026"})
    with pytest.raises(RegistryError, match="provenance.published_at is not an ISO date"):
        load_registry(_write(tmp_path, [entry]))


def test_effective_inversion_is_rejected(tmp_path: Path) -> None:
    entry = _entry(effective={"from": "2026-05-01", "to": "2026-04-01"})
    with pytest.raises(RegistryError, match="effective.to is before effective.from"):
        load_registry(_write(tmp_path, [entry]))


def test_effective_invalid_date_is_rejected(tmp_path: Path) -> None:
    entry = _entry(effective={"from": "May 2026", "to": None})
    with pytest.raises(RegistryError, match="effective.from is not an ISO date"):
        load_registry(_write(tmp_path, [entry]))


def test_quality_negative_anchors_is_rejected(tmp_path: Path) -> None:
    entry = _entry(quality={"anchors": -1})
    with pytest.raises(RegistryError, match="quality.anchors must be a non-negative integer"):
        load_registry(_write(tmp_path, [entry]))


def test_supersedes_self_is_rejected(tmp_path: Path) -> None:
    entry = _entry(supersedes="POL-TEST-001")
    with pytest.raises(RegistryError, match="must not point at the entry itself"):
        load_registry(_write(tmp_path, [entry]))


def test_unknown_source_record_schema_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="source_record_schema"):
        load_registry(_write(tmp_path, [_entry(source_record_schema=6)]))


def test_provenance_must_be_a_mapping(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="provenance is not a mapping"):
        load_registry(_write(tmp_path, [_entry(provenance="not-a-mapping")]))


def test_effective_must_be_a_mapping(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="effective is not a mapping"):
        load_registry(_write(tmp_path, [_entry(effective="2026-01-01")]))


def test_quality_must_be_a_mapping(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="quality is not a mapping"):
        load_registry(_write(tmp_path, [_entry(quality=[1, 2])]))


def test_schema_yaml_publishes_v5_surface() -> None:
    schema = yaml.safe_load((ROOT / "configs" / "schema.yaml").read_text(encoding="utf-8"))
    assert schema["source_record_schema"] == 5
    source = schema["source"]
    assert source["levels"] == [
        "national",
        "provincial",
        "municipal",
        "international",
        "non_official",
    ]
    assert source["authority_tiers"] == ["A", "B", "C", "D"]
    assert "licensed" in source["licenses"]
    assert "web" in source["channels"]
    assert "provenance_fields" in source
    assert "effective_fields" in source
    assert "quality_fields" in source
    assert "practical_guide" in source["source_classes"]
    assert source["ingest_tiers"] == ["canonical", "provisional"]
    assert source["authority_score"] == {"min": 0, "max": 5}
