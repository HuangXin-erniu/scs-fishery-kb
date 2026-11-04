from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from scs_fkb.candidates import (
    CandidateError,
    check_candidates,
    load_candidates,
    propose_from_watch,
    validate_candidate,
)


def _candidate(**overrides):
    candidate = {
        "id": "CAND-2026-001",
        "title": "New closure notice",
        "url": "https://www.moa.gov.cn/example",
        "publisher": "农业农村部",
        "proposed_tier": "A",
        "proposed_class": "normative",
        "reason": "changed",
        "watch_ref": "WATCH-MOA-CLOSURE-2023",
        "first_seen": "2026-11-04",
        "expires_at": "2027-05-03",
        "status": "open",
        "decision_key": None,
        "source_id": None,
        "note": "",
    }
    candidate.update(overrides)
    return candidate


def _write(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / "candidates.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "candidates": items}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_empty_register_loads(tmp_path: Path) -> None:
    assert load_candidates(_write(tmp_path, [])) == []


def test_valid_candidate_loads(tmp_path: Path) -> None:
    assert load_candidates(_write(tmp_path, [_candidate()]))[0]["id"] == "CAND-2026-001"


def test_duplicate_url_is_rejected(tmp_path: Path) -> None:
    first = _candidate()
    second = _candidate(id="CAND-2026-002", url="https://www.moa.gov.cn/example/")
    with pytest.raises(CandidateError, match="duplicate url"):
        load_candidates(_write(tmp_path, [first, second]))


def test_accepted_without_source_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CandidateError, match="needs source_id"):
        load_candidates(_write(tmp_path, [_candidate(status="accepted")]))


def test_rejected_without_note_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CandidateError, match="needs a note"):
        load_candidates(_write(tmp_path, [_candidate(status="rejected")]))


def test_unknown_status_and_reason_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CandidateError, match="status"):
        load_candidates(_write(tmp_path, [_candidate(status="pending")]))
    with pytest.raises(CandidateError, match="reason"):
        load_candidates(_write(tmp_path, [_candidate(reason="rumour")]))


def test_expired_open_candidate_is_reported(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _candidate(
                first_seen="2026-04-01",
                expires_at="2026-10-01",
            )
        ],
    )
    report = check_candidates(path, today=date(2026, 11, 4))
    assert [row["id"] for row in report["expired"]] == ["CAND-2026-001"]
    assert report["expired"][0]["days_past"] == 34


def test_open_candidate_is_due_after_ninety_days(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _candidate(
                first_seen="2026-07-01",
                expires_at="2027-01-01",
            )
        ],
    )
    report = check_candidates(path, today=date(2026, 11, 4))
    assert [row["id"] for row in report["due"]] == ["CAND-2026-001"]
    assert report["due"][0]["days_open"] == 126


def test_accepted_source_must_exist_in_registry(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _candidate(
                status="accepted",
                source_id="POL-MISSING-999",
                decision_key="D-TEST",
            )
        ],
    )
    report = check_candidates(path, today=date(2026, 11, 4), registry_ids={"POL-LAW-009"})
    assert any("not in the registry" in error for error in report["errors"])


def test_propose_from_watch_maps_changed_and_new_entries() -> None:
    report = {
        "checked_at": "2026-11-04T00:00:00+00:00",
        "results": [
            {
                "id": "WATCH-A",
                "title": "Closure page",
                "publisher": "农业农村部",
                "url": "https://www.moa.gov.cn/a",
                "authority": "A",
                "status": "changed",
            },
            {
                "id": "WATCH-B",
                "title": "Gazette",
                "publisher": "农业农村部",
                "url": "https://www.moa.gov.cn/b",
                "authority": "B",
                "status": "unbaselined",
            },
            {
                "id": "WATCH-C",
                "title": "Stable",
                "publisher": "农业农村部",
                "url": "https://www.moa.gov.cn/c",
                "authority": "A",
                "status": "ok",
            },
        ],
    }
    proposals = propose_from_watch(report, [], today=date(2026, 11, 4))
    assert [item["id"] for item in proposals] == ["CAND-2026-001", "CAND-2026-002"]
    assert [item["reason"] for item in proposals] == ["changed", "new"]
    assert proposals[0]["expires_at"] == "2027-05-03"
    assert proposals[0]["watch_ref"] == "WATCH-A"
    assert all(validate_candidate(item) == [] for item in proposals)


def test_propose_from_watch_skips_known_refs_and_urls() -> None:
    report = {
        "results": [
            {
                "id": "WATCH-A",
                "publisher": "农业农村部",
                "url": "https://www.moa.gov.cn/a",
                "authority": "A",
                "status": "changed",
            },
            {
                "id": "WATCH-B",
                "publisher": "农业农村部",
                "url": "https://www.moa.gov.cn/b/",
                "authority": "A",
                "status": "changed",
            },
        ]
    }
    existing = [
        _candidate(watch_ref="WATCH-A"),
        _candidate(
            id="CAND-2026-002",
            watch_ref="OTHER",
            url="https://www.moa.gov.cn/b",
        ),
    ]
    assert propose_from_watch(report, existing, today=date(2026, 11, 4)) == []


def test_candidate_id_and_date_validation() -> None:
    assert validate_candidate(_candidate(id="CAND-26-1"))
    assert validate_candidate(_candidate(expires_at="2026-01-01"))
