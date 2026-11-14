from __future__ import annotations

from datetime import date

from scs_fkb.registry import validate_entry
from scs_fkb.update.review import review_candidate

CANDIDATE = {
    "id": "CAND-2026-001",
    "title": "休渔期安全提示",
    "url": "https://example.org/notice",
    "publisher": "示例渔业局",
    "proposed_tier": "A",
    "proposed_class": "reference",
    "reason": "gap",
    "first_seen": "2026-11-12",
    "expires_at": "2027-05-11",
    "status": "open",
}


def test_review_package_accepts_a_complete_candidate() -> None:
    package = review_candidate(
        CANDIDATE,
        text_chars=1200,
        sha256="a" * 64,
        license_value="public",
        sensitivity="public",
        practical_domain="safety",
        today=date(2026, 11, 12),
    )
    assert package.acceptable is True
    assert package.entry is not None
    assert package.entry["ingest"]["tier"] == "provisional"
    assert package.entry["practical"]["domain"] == "safety"
    assert validate_entry(package.entry) == []
    assert "inspect_page_and_licence" in package.actions


def test_review_package_rejects_short_or_unlicensed_candidate() -> None:
    short = review_candidate(
        CANDIDATE,
        text_chars=10,
        sha256="a" * 64,
        license_value="public",
        sensitivity="public",
    )
    assert short.acceptable is False
    assert "text_too_short" in short.quality.reasons
    unlicensed = review_candidate(
        CANDIDATE,
        text_chars=1200,
        sha256="a" * 64,
        license_value="unknown",
        sensitivity="public",
    )
    assert unlicensed.acceptable is False
    assert "license_unknown" in unlicensed.quality.reasons


def test_review_package_serializes() -> None:
    package = review_candidate(
        CANDIDATE,
        text_chars=1200,
        sha256="a" * 64,
        license_value="public",
        sensitivity="public",
    )
    payload = package.to_dict()
    assert payload["candidate_id"] == "CAND-2026-001"
    assert payload["quality"]["passed"] is True
