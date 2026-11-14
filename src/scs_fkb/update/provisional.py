"""Build a provisional source entry from a changed candidate.

A provisional entry may answer with a visible label, but it cannot alone support
a rule, status, quantity or warning and it is not a canonical source.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..registry import AUTHORITY_SCORE, TTL_BY_CADENCE, validate_entry
from .quality import QualityReport

TIER_LEVEL = {"A": "national", "B": "national", "C": "municipal", "D": "non_official"}
PROVISIONAL_REVIEW_DAYS = 30


class ProvisionalError(RuntimeError):
    """Raised when a provisional entry cannot be built or validated."""


def plan_provisional(
    candidate: dict[str, Any],
    quality: QualityReport,
    *,
    today: date,
    source_id: str = "",
    license_value: str = "public",
    sensitivity: str = "public",
    practical_domain: str = "other",
    practical_personas: list[str] | None = None,
    task_tags: list[str] | None = None,
    seasonal: bool = False,
) -> dict[str, Any]:
    """Return a validated v5 provisional entry; never writes the register."""
    if not quality.passed:
        raise ProvisionalError("quality gate failed: " + ",".join(quality.reasons))
    if not quality.content_hash:
        raise ProvisionalError("a provisional entry needs a content hash")
    tier = str(candidate.get("proposed_tier") or "C").strip().upper()
    if tier not in TIER_LEVEL:
        raise ProvisionalError(f"unknown authority tier: {tier!r}")
    level = str(candidate.get("proposed_level") or TIER_LEVEL[tier])
    source_class = str(candidate.get("proposed_class") or "reference")
    identifier = source_id or f"PROV-{candidate.get('id') or 'CAND'}"
    review_due = (today + timedelta(days=PROVISIONAL_REVIEW_DAYS)).isoformat()
    ttl_days = TTL_BY_CADENCE.get("monthly", 30)
    entry: dict[str, Any] = {
        "id": identifier,
        "source_record_schema": 5,
        "title": str(candidate.get("title") or identifier),
        "status": "acquired",
        "level": level,
        "authority_tier": tier,
        "source_class": source_class,
        "currency": {
            "as_of": today.isoformat(),
            "basis": "retrieval",
            "review_due": review_due,
            "cadence": "monthly",
            "ttl_days": ttl_days,
            "note": "provisional watch diff",
        },
        "retrieval": {
            "channel": "main",
            "parseable": True,
            "note": "provisional candidate; review before canonical promotion",
        },
        "lifecycle": "active",
        "license": license_value,
        "sensitivity": sensitivity,
        "hash": quality.content_hash,
        "location": f"snapshots/{identifier}/{quality.content_hash[:12]}",
        "provenance": {
            "url": str(candidate.get("url") or ""),
            "document_no": None,
            "published_at": None,
            "retrieved_at": today.isoformat(),
            "sha256": quality.content_hash,
            "bytes": None,
            "mime": None,
            "snapshot_path": f"snapshots/{identifier}/{quality.content_hash[:12]}",
        },
        "effective": {"from": None, "to": None},
        "quality": {
            "text_layer": True,
            "anchors": 0,
            "tables": 0,
            "ocr": False,
            "quarantine_reason": None,
            "text_coverage": quality.text_coverage,
            "anchor_coverage": 0.0,
            "table_count": 0,
            "ocr_confidence": None,
        },
        "authority": {
            "score": AUTHORITY_SCORE.get(tier, 0),
            "evidence_url": str(candidate.get("url") or ""),
        },
        "license_evidence": {
            "url": str(candidate.get("url") or ""),
            "text": str(candidate.get("license_note") or "") or None,
            "checked_at": today.isoformat(),
        },
        "ingest": {
            "tier": "provisional",
            "reviewed_by": None,
            "reviewed_at": None,
            "review_note": "watch diff; provisional until human review",
        },
        "practical": {
            "domain": practical_domain,
            "personas": practical_personas or [],
            "task_tags": task_tags or [],
            "seasonal": seasonal,
        },
        "license_note": candidate.get("license_note"),
        "supersedes": candidate.get("supersedes"),
        "superseded_by": None,
    }
    errors = validate_entry(entry)
    if errors:
        raise ProvisionalError("; ".join(errors))
    return entry


__all__ = ["PROVISIONAL_REVIEW_DAYS", "ProvisionalError", "TIER_LEVEL", "plan_provisional"]
