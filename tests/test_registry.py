from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.registry import RegistryError, load_registry, select


def _entry(**overrides):
    entry = {
        "id": "POL-TEST-001",
        "title": "test",
        "status": "acquired",
        "level": "national",
        "authority_tier": "A",
        "validity": {"status": "in_force", "as_of": "2026-11-02", "note": "current"},
        "retrieval": {"channel": "collection", "parseable": True, "note": "registered"},
        "lifecycle": "active",
    }
    entry.update(overrides)
    return entry


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "corpus.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "sources": entries}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_valid_registry_loads(tmp_path: Path) -> None:
    registry = load_registry(_write(tmp_path, [_entry()]))
    assert registry["POL-TEST-001"]["level"] == "national"


def test_missing_level_is_rejected(tmp_path: Path) -> None:
    entry = _entry()
    del entry["level"]
    with pytest.raises(RegistryError, match="missing level"):
        load_registry(_write(tmp_path, [entry]))


def test_bad_authority_tier_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="authority_tier"):
        load_registry(_write(tmp_path, [_entry(authority_tier="Z")]))


def test_unknown_validity_status_is_rejected(tmp_path: Path) -> None:
    entry = _entry(validity={"status": "maybe", "as_of": "2026-11-02", "note": "x"})
    with pytest.raises(RegistryError, match="validity.status"):
        load_registry(_write(tmp_path, [entry]))


def test_retired_requires_retirement_block(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="retirement"):
        load_registry(_write(tmp_path, [_entry(lifecycle="retired")]))


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="duplicate id"):
        load_registry(_write(tmp_path, [_entry(), _entry()]))


def test_bad_retrieval_channel_is_rejected(tmp_path: Path) -> None:
    entry = _entry(retrieval={"channel": "ftp", "parseable": True, "note": "x"})
    with pytest.raises(RegistryError, match="retrieval.channel"):
        load_registry(_write(tmp_path, [entry]))


def test_non_boolean_parseable_is_rejected(tmp_path: Path) -> None:
    entry = _entry(retrieval={"channel": "none", "parseable": "yes", "note": "x"})
    with pytest.raises(RegistryError, match="parseable"):
        load_registry(_write(tmp_path, [entry]))


def test_select_filters_by_level_and_channel() -> None:
    sources = {
        "A": _entry(id="A", level="national"),
        "B": _entry(id="B", level="provincial"),
        "C": _entry(
            id="C", level="national", retrieval={"channel": "main", "parseable": True, "note": "x"}
        ),
    }
    assert [entry["id"] for entry in select(sources, level="national")] == ["A", "C"]
    assert [entry["id"] for entry in select(sources, channel="main")] == ["C"]
