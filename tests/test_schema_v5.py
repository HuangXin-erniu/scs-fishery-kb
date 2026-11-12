from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.registry import RegistryError, load_registry, normalize_entry

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def _entry(**overrides):
    entry = {
        "id": "POL-V5-001",
        "title": "v5 test",
        "status": "acquired",
        "level": "national",
        "authority_tier": "A",
        "source_class": "practical_guide",
        "currency": {
            "as_of": "2026-11-03",
            "basis": "publication",
            "review_due": "2026-12-03",
            "cadence": "monthly",
            "ttl_days": 30,
        },
        "retrieval": {"channel": "main", "parseable": True, "note": "registered"},
        "lifecycle": "active",
        "license": "public",
        "sensitivity": "public",
        "hash": HASH,
        "location": "raw/POL-V5-001/test.html",
        "license_evidence": {
            "url": "https://example.org/page",
            "checked_at": "2026-11-03",
        },
        "ingest": {
            "tier": "canonical",
            "reviewed_by": "owner",
            "reviewed_at": "2026-11-03",
            "review_note": "reviewed",
        },
        "practical": {
            "domain": "safety",
            "personas": ["captain", "crew"],
            "task_tags": ["closure", "safety"],
            "seasonal": True,
        },
    }
    entry.update(overrides)
    return entry


def _write(tmp_path: Path, entries: list[dict], schema: int = 5) -> Path:
    path = tmp_path / "corpus.yaml"
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "source_record_schema": schema, "sources": entries},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def test_v4_entry_is_upgraded_with_v5_defaults() -> None:
    entry = _entry(source_record_schema=4)
    entry.pop("ingest")
    entry.pop("practical")
    entry.pop("license_evidence")
    entry["currency"].pop("ttl_days")
    normalized = normalize_entry(entry)
    assert normalized["source_record_schema"] == 5
    assert normalized["ingest"]["tier"] == "canonical"
    assert normalized["practical"]["domain"] == ""
    assert normalized["currency"]["ttl_days"] == 30
    assert normalized["license_evidence"]["checked_at"] == "2026-11-03"


def test_provisional_source_is_accepted(tmp_path: Path) -> None:
    entry = _entry(
        ingest={
            "tier": "provisional",
            "reviewed_by": None,
            "reviewed_at": None,
            "review_note": "watch diff 2026-11-12",
        }
    )
    registry = load_registry(_write(tmp_path, [entry]))
    assert registry["POL-V5-001"]["ingest"]["tier"] == "provisional"


def test_provisional_requires_review_note(tmp_path: Path) -> None:
    entry = _entry(
        ingest={"tier": "provisional", "reviewed_by": None, "reviewed_at": None, "review_note": ""}
    )
    with pytest.raises(RegistryError, match="provisional source needs ingest.review_note"):
        load_registry(_write(tmp_path, [entry]))


def test_canonical_practical_requires_license_evidence(tmp_path: Path) -> None:
    entry = _entry(license_evidence={"url": None, "text": None, "checked_at": None})
    with pytest.raises(RegistryError, match="canonical practical source needs license_evidence"):
        load_registry(_write(tmp_path, [entry]))


def test_invalid_practical_domain_is_rejected(tmp_path: Path) -> None:
    entry = _entry(practical={"domain": "space", "personas": [], "task_tags": []})
    with pytest.raises(RegistryError, match="practical.domain"):
        load_registry(_write(tmp_path, [entry]))


def test_invalid_practical_persona_is_rejected(tmp_path: Path) -> None:
    entry = _entry(practical={"domain": "safety", "personas": ["alien"], "task_tags": []})
    with pytest.raises(RegistryError, match="practical.persona"):
        load_registry(_write(tmp_path, [entry]))


def test_authority_score_range_is_enforced(tmp_path: Path) -> None:
    entry = _entry(authority={"score": 7})
    with pytest.raises(RegistryError, match="authority.score"):
        load_registry(_write(tmp_path, [entry]))


def test_ttl_must_be_positive(tmp_path: Path) -> None:
    entry = _entry()
    entry["currency"]["ttl_days"] = 0
    with pytest.raises(RegistryError, match="currency.ttl_days"):
        load_registry(_write(tmp_path, [entry]))


def test_quality_coverage_range_is_enforced(tmp_path: Path) -> None:
    entry = _entry(quality={"text_coverage": 1.5})
    with pytest.raises(RegistryError, match="quality.text_coverage"):
        load_registry(_write(tmp_path, [entry]))


def test_supersession_must_be_symmetric(tmp_path: Path) -> None:
    newer = _entry(id="POL-V5-002", supersedes="POL-V5-001")
    older = _entry(id="POL-V5-001")
    with pytest.raises(RegistryError, match="does not point back"):
        load_registry(_write(tmp_path, [newer, older]))


def test_supersession_both_directions_is_accepted(tmp_path: Path) -> None:
    older = _entry(id="POL-V5-001", superseded_by="POL-V5-002")
    newer = _entry(id="POL-V5-002", supersedes="POL-V5-001")
    registry = load_registry(_write(tmp_path, [older, newer]))
    assert registry["POL-V5-002"]["supersedes"] == "POL-V5-001"
    assert registry["POL-V5-001"]["superseded_by"] == "POL-V5-002"


def test_live_register_loads_as_v5() -> None:
    registry = load_registry(ROOT / "configs" / "corpus.yaml")
    assert registry
    assert all(source["source_record_schema"] == 5 for source in registry.values())
    tiers = [source["ingest"]["tier"] for source in registry.values()]
    assert tiers.count("canonical") == 106
    assert tiers.count("provisional") == 5
    assert all(isinstance(source["currency"]["ttl_days"], int) for source in registry.values())
