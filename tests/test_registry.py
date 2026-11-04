from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from scs_fkb.registry import (
    RegistryError,
    check_currency,
    load_registry,
    select,
    validate_watch_coverage,
)


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
        "retrieval": {"channel": "collection", "parseable": True, "note": "registered"},
        "lifecycle": "active",
        "license": "public",
        "sensitivity": "public",
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


def test_bad_source_class_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="source_class"):
        load_registry(_write(tmp_path, [_entry(source_class="current")]))


def test_legacy_validity_is_rejected(tmp_path: Path) -> None:
    entry = _entry()
    del entry["source_class"]
    del entry["currency"]
    entry["validity"] = {"status": "in_force", "as_of": "2026-11-02", "note": "x"}
    with pytest.raises(RegistryError, match="validity is retired"):
        load_registry(_write(tmp_path, [entry]))


def test_bad_basis_is_rejected(tmp_path: Path) -> None:
    entry = _entry(currency={"as_of": "2026-11-03", "basis": "guess", "review_due": "2026-12-03"})
    with pytest.raises(RegistryError, match="currency.basis"):
        load_registry(_write(tmp_path, [entry]))


def test_malformed_currency_date_is_rejected(tmp_path: Path) -> None:
    entry = _entry(
        currency={"as_of": "03/11/2026", "basis": "publication", "review_due": "2026-12-03"}
    )
    with pytest.raises(RegistryError, match="currency.as_of"):
        load_registry(_write(tmp_path, [entry]))


def test_review_due_before_as_of_is_rejected(tmp_path: Path) -> None:
    entry = _entry(
        currency={"as_of": "2026-11-03", "basis": "publication", "review_due": "2026-01-01"}
    )
    with pytest.raises(RegistryError, match="review_due is before as_of"):
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


def test_reference_class_is_accepted(tmp_path: Path) -> None:
    entry = _entry(
        source_class="reference",
        currency={
            "as_of": "2026-11-03",
            "basis": "retrieval",
            "review_due": "2027-05-02",
            "cadence": "semiannual",
        },
    )
    registry = load_registry(_write(tmp_path, [entry]))
    assert registry["POL-TEST-001"]["source_class"] == "reference"


def test_missing_cadence_is_rejected(tmp_path: Path) -> None:
    entry = _entry()
    del entry["currency"]["cadence"]
    with pytest.raises(RegistryError, match="currency.cadence"):
        load_registry(_write(tmp_path, [entry]))


def test_unknown_cadence_is_rejected(tmp_path: Path) -> None:
    entry = _entry(currency={**_entry()["currency"], "cadence": "sometimes"})
    with pytest.raises(RegistryError, match="currency.cadence"):
        load_registry(_write(tmp_path, [entry]))


def test_review_due_beyond_cadence_cap_is_rejected(tmp_path: Path) -> None:
    entry = _entry(
        currency={
            "as_of": "2026-11-03",
            "basis": "publication",
            "review_due": "2027-01-03",
            "cadence": "monthly",
        }
    )
    with pytest.raises(RegistryError, match="beyond the 60-day cap"):
        load_registry(_write(tmp_path, [entry]))


def test_review_due_at_cadence_cap_is_accepted(tmp_path: Path) -> None:
    entry = _entry(
        currency={
            "as_of": "2026-11-03",
            "basis": "publication",
            "review_due": "2027-01-02",
            "cadence": "monthly",
        }
    )
    assert (
        load_registry(_write(tmp_path, [entry]))["POL-TEST-001"]["currency"]["cadence"] == "monthly"
    )


def test_tier_c_requires_municipal(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="authority_tier C requires level municipal"):
        load_registry(_write(tmp_path, [_entry(authority_tier="C")]))


def test_municipal_source_cannot_be_tier_a(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="cannot be municipal"):
        load_registry(_write(tmp_path, [_entry(level="municipal")]))


def test_unknown_license_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="license"):
        load_registry(_write(tmp_path, [_entry(license="all-rights-reserved")]))


def test_unknown_sensitivity_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="sensitivity"):
        load_registry(_write(tmp_path, [_entry(sensitivity="secret")]))


def test_check_currency_grace_boundary() -> None:
    registry = {"A": _entry()}
    assert check_currency(registry, today=date(2027, 1, 2), grace_days=30)["overdue"] == []
    late = check_currency(registry, today=date(2027, 1, 3), grace_days=30)
    assert [row["id"] for row in late["overdue"]] == ["A"]
    assert late["overdue"][0]["days_overdue"] == 31


def test_check_currency_skips_retired_sources() -> None:
    registry = {
        "A": _entry(
            lifecycle="retired",
            retirement={"date": "2026-11-01", "reason": "superseded", "decision_key": "D-TEST"},
        )
    }
    assert check_currency(registry, today=date(2027, 1, 3))["overdue"] == []


def _watched(**overrides):
    entry = _entry(**overrides)
    return entry


def test_watch_coverage_accepts_a_reference() -> None:
    registry = {"A": _watched(watch_ref="WATCH-1")}
    validate_watch_coverage(registry, [{"id": "WATCH-1"}])


def test_watch_coverage_accepts_a_note() -> None:
    registry = {"A": _watched(watch_note="static text; reviewed quarterly")}
    validate_watch_coverage(registry, [])


def test_watch_coverage_rejects_a_missing_link() -> None:
    with pytest.raises(RegistryError, match="neither watch_ref nor watch_note"):
        validate_watch_coverage({"A": _watched()}, [{"id": "WATCH-1"}])


def test_watch_coverage_rejects_an_unknown_reference() -> None:
    with pytest.raises(RegistryError, match="not in the watch list"):
        validate_watch_coverage({"A": _watched(watch_ref="WATCH-9")}, [{"id": "WATCH-1"}])
