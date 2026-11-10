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


def _candidate(**overrides: object) -> dict:
    row = {
        "id": "CAND-2026-001",
        "title": "2026 closure notice",
        "url": "https://www.moa.gov.cn/a",
        "publisher": "农业农村部",
        "proposed_tier": "A",
        "reason": "new",
        "first_seen": "2026-11-10",
        "expires_at": "2027-05-09",
        "status": "open",
    }
    row.update(overrides)
    return row


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "candidates.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "candidates": rows}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_empty_candidate_register_loads(tmp_path: Path) -> None:
    path = _write(tmp_path, [])
    assert load_candidates(path) == []
    summary = check_candidates(path, today=date(2026, 11, 10))
    assert summary["total"] == 0
    assert summary["counts"] == {"accepted": 0, "expired": 0, "open": 0, "rejected": 0}


def test_invalid_candidate_is_rejected(tmp_path: Path) -> None:
    errors = validate_candidate(_candidate(proposed_tier="Z", status="open"))
    assert any("proposed_tier" in error for error in errors)

    path = _write(tmp_path, [_candidate(), _candidate()])
    with pytest.raises(CandidateError, match="duplicate"):
        load_candidates(path)


def test_accepted_candidate_requires_a_source_id() -> None:
    errors = validate_candidate(_candidate(status="accepted"))
    assert any("source_id" in error for error in errors)


def test_open_candidate_expiry_and_due_are_reported(tmp_path: Path) -> None:
    expired = _candidate(id="CAND-2026-001", expires_at="2026-01-01", first_seen="2025-01-01")
    due = _candidate(
        id="CAND-2026-002",
        url="https://www.moa.gov.cn/b",
        first_seen="2026-01-01",
        expires_at="2027-01-01",
    )
    summary = check_candidates(_write(tmp_path, [expired, due]), today=date(2026, 11, 10))
    assert [row["id"] for row in summary["expired"]] == ["CAND-2026-001"]
    assert [row["id"] for row in summary["due"]] == ["CAND-2026-002"]


def test_propose_from_watch_is_pure_and_skips_active_refs() -> None:
    report = {
        "results": [
            {
                "id": "WATCH-MOA-1",
                "title": "Changed page",
                "url": "https://www.moa.gov.cn/changed",
                "publisher": "农业农村部",
                "authority": "A",
                "status": "changed",
            },
            {
                "id": "WATCH-MOA-2",
                "title": "Already tracked",
                "url": "https://www.moa.gov.cn/tracked",
                "publisher": "农业农村部",
                "authority": "A",
                "status": "changed",
            },
        ]
    }
    existing = [
        _candidate(
            watch_ref="WATCH-MOA-2",
            url="https://www.moa.gov.cn/tracked",
        )
    ]
    proposals = propose_from_watch(report, existing, today=date(2026, 11, 10))
    assert len(proposals) == 1
    assert proposals[0]["id"] == "CAND-2026-002"
    assert proposals[0]["watch_ref"] == "WATCH-MOA-1"
    assert proposals[0]["status"] == "open"
