from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scs_fkb.registry import validate_entry
from scs_fkb.update import (
    assess,
    assess_candidate,
    changes_from_watch,
    plan_provisional,
    promotion_draft,
    run_cycle,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
TODAY = date(2026, 11, 12)


def _candidate(**extra):
    row = {
        "id": "CAND-2026-001",
        "title": "休渔期安全提示",
        "url": "https://example.org/notice",
        "publisher": "示例渔业局",
        "proposed_tier": "A",
        "proposed_class": "reference",
        "reason": "changed",
        "first_seen": "2026-11-12",
        "expires_at": "2027-05-11",
        "status": "open",
        "license": "public",
        "sensitivity": "public",
        "text_chars": 1200,
        "parseable": True,
        "sha256": HASH_A,
    }
    row.update(extra)
    return row


def _registry_entry():
    return {
        "id": "POL-EXIST-001",
        "title": "existing",
        "status": "acquired",
        "level": "national",
        "authority_tier": "A",
        "source_class": "normative",
        "currency": {
            "as_of": "2026-11-02",
            "basis": "publication",
            "review_due": "2026-12-02",
            "cadence": "monthly",
        },
        "retrieval": {"channel": "main", "parseable": True, "note": "registered"},
        "lifecycle": "active",
        "license": "public",
        "sensitivity": "public",
        "hash": HASH_B,
        "location": "raw/POL-EXIST-001/test.html",
    }


def _write_yaml(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def _watch_report(*, text_chars: int = 1200, sha256: str = HASH_A) -> dict:
    return {
        "results": [
            {
                "id": "W-001",
                "title": "watch row",
                "url": "https://example.org/notice",
                "publisher": "示例渔业局",
                "authority": "A",
                "status": "changed",
                "sha256": sha256,
                "text_chars": text_chars,
                "http_status": 200,
            }
        ]
    }


def test_diff_selects_only_changed_or_unbaselined() -> None:
    report = {
        "results": [
            {"id": "a", "status": "ok", "url": "https://a"},
            {"id": "b", "status": "changed", "url": "https://b", "sha256": HASH_A},
            {"id": "c", "status": "unreachable", "url": "https://c"},
            {"id": "d", "status": "unbaselined", "url": "https://d"},
        ]
    }
    changes = changes_from_watch(report, {"b": HASH_B})
    assert [item.watch_id for item in changes] == ["b", "d"]
    assert changes[0].baseline_sha256 == HASH_B


def test_quality_gate_passes_and_rejects() -> None:
    good = assess(
        text_chars=1200,
        parseable=True,
        license_value="public",
        sensitivity_value="public",
        content_hash=HASH_A,
    )
    assert good.passed is True
    assert good.reasons == ()
    bad = assess(
        text_chars=10,
        parseable=False,
        license_value="unknown",
        sensitivity_value="unknown",
        content_hash=HASH_A,
        seen_hashes={HASH_A},
    )
    assert bad.passed is False
    assert {"not_parseable", "text_too_short", "license_unknown", "sensitivity_unknown"} <= set(
        bad.reasons
    )
    duplicate = assess(
        text_chars=1200,
        parseable=True,
        license_value="public",
        sensitivity_value="public",
        content_hash=HASH_A,
        seen_hashes={HASH_A},
    )
    assert "duplicate_content" in duplicate.reasons


def test_provisional_entry_validates() -> None:
    candidate = _candidate()
    quality = assess_candidate(candidate)
    entry = plan_provisional(candidate, quality, today=TODAY)
    assert entry["ingest"]["tier"] == "provisional"
    assert entry["practical"]["domain"] == "other"
    assert entry["id"].startswith("PROV-")
    assert validate_entry(entry) == []


def test_promotion_draft_becomes_canonical() -> None:
    candidate = _candidate()
    quality = assess_candidate(candidate)
    provisional = plan_provisional(candidate, quality, today=TODAY)
    draft = promotion_draft(
        provisional,
        source_id="POL-NEW-001",
        reviewer="owner",
        today=TODAY,
    )
    entry = draft["entry"]
    assert entry["id"] == "POL-NEW-001"
    assert entry["ingest"]["tier"] == "canonical"
    assert entry["ingest"]["reviewed_by"] == "owner"
    assert validate_entry(entry) == []
    assert "rebuild_index" in draft["actions"]


def test_cycle_writes_plan_without_touching_registry(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "corpus.yaml",
        {"schema_version": 1, "source_record_schema": 5, "sources": [_registry_entry()]},
    )
    candidates_path = _write_yaml(
        tmp_path / "candidates.yaml",
        {
            "schema_version": 1,
            "updated_at": "2026-11-12",
            "candidates": [_candidate()],
        },
    )
    before = registry_path.read_bytes()
    summary = run_cycle(
        run_root=tmp_path / "runs",
        today=TODAY,
        registry_path=registry_path,
        candidates_path=candidates_path,
        watch_report=_watch_report(),
        live=False,
    )
    assert summary["changes"] == 1
    assert summary["matched"] == 1
    assert len(summary["plans"]) == 1
    assert summary["plans"][0]["entry"]["ingest"]["tier"] == "provisional"
    assert Path(summary["report"]).is_file()
    assert (tmp_path / "runs" / "update" / "2026-11-12.json").is_file()
    assert registry_path.read_bytes() == before


def test_cycle_rejects_short_or_unlicensed_change(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "corpus.yaml",
        {"schema_version": 1, "source_record_schema": 5, "sources": [_registry_entry()]},
    )
    candidates_path = _write_yaml(
        tmp_path / "candidates.yaml",
        {
            "schema_version": 1,
            "updated_at": "2026-11-12",
            "candidates": [_candidate(license="unknown", sensitivity="unknown")],
        },
    )
    summary = run_cycle(
        run_root=tmp_path / "runs",
        today=TODAY,
        registry_path=registry_path,
        candidates_path=candidates_path,
        watch_report=_watch_report(text_chars=10),
        live=False,
    )
    assert summary["plans"] == []
    assert summary["rejected"]
    assert "license_unknown" in summary["rejected"][0]["reasons"]


def test_cycle_reports_uncandidated_change(tmp_path: Path) -> None:
    registry_path = _write_yaml(
        tmp_path / "corpus.yaml",
        {"schema_version": 1, "source_record_schema": 5, "sources": [_registry_entry()]},
    )
    candidates_path = _write_yaml(
        tmp_path / "candidates.yaml",
        {"schema_version": 1, "updated_at": "2026-11-12", "candidates": []},
    )
    summary = run_cycle(
        run_root=tmp_path / "runs",
        today=TODAY,
        registry_path=registry_path,
        candidates_path=candidates_path,
        watch_report=_watch_report(),
        live=False,
    )
    assert summary["rejected"][0]["stage"] == "no_candidate"
