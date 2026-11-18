"""Shared provenance rules for human-review artifacts.

A worksheet or signature only counts as human evidence when its provenance says
so.  The point is to make it hard for an AI-filled file to be scored as a human
signature by accident: the acceptance scripts refuse to treat
``reviewer_type != "human"`` (or a missing type) as a human sign-off.
"""

from __future__ import annotations

import json
from pathlib import Path

HUMAN = "human"
NON_HUMAN = {"ai", "ai_assistant", "assistant", "llm", "model", "automated", "machine"}


def load(path: str | Path | None) -> dict:
    """Load a provenance JSON object; return {} when absent or invalid."""
    if not path:
        return {}
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def reviewer_kind(provenance: dict | None) -> str:
    """Return human / non_human / unknown / missing for a provenance object."""
    if not provenance:
        return "missing"
    raw = (
        str(provenance.get("reviewer_type") or provenance.get("reviewed_by_type") or "")
        .strip()
        .lower()
    )
    if raw == HUMAN:
        return HUMAN
    if raw in NON_HUMAN:
        return "non_human"
    return "unknown"


def check_human(provenance: dict | None, *, require_attestation: bool = False) -> tuple[bool, str]:
    """Return (is_human, reason).  Only a human provenance may sign acceptance."""
    kind = reviewer_kind(provenance)
    if kind != HUMAN:
        return False, f"reviewer_type={kind}; only reviewer_type=human counts as human evidence"
    if require_attestation and not str((provenance or {}).get("attestation") or "").strip():
        return False, "human signature missing attestation"
    return True, "human"


def from_csv_row(row: dict) -> dict:
    """Build a provenance object from optional reviewer_* columns in a CSV row."""
    return {
        "reviewer_type": row.get("reviewer_type", ""),
        "reviewed_by": row.get("reviewed_by", ""),
        "reviewed_at": row.get("reviewed_at", ""),
        "attestation": row.get("attestation", ""),
    }
