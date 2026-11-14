"""Promotion draft: turn a reviewed provisional entry into a canonical one."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

from ..registry import CADENCE_CAPS, validate_entry

PROMOTION_ACTIONS = (
    "capture_snapshot",
    "register_source",
    "rebuild_processed",
    "rebuild_index",
    "run_regression",
    "record_project_log",
)


class PromotionError(RuntimeError):
    """Raised when a provisional entry cannot be promoted."""


def promotion_draft(
    provisional: dict[str, Any],
    *,
    source_id: str,
    reviewer: str,
    today: date,
    cadence: str = "monthly",
    review_days: int = 30,
) -> dict[str, Any]:
    """Return a canonical entry plus the human/CI actions that still must run."""
    if (provisional.get("ingest") or {}).get("tier") != "provisional":
        raise PromotionError("only a provisional entry can be promoted")
    if not str(reviewer or "").strip():
        raise PromotionError("promotion requires a reviewer")
    if not str(source_id or "").strip():
        raise PromotionError("promotion requires a canonical source id")
    entry = deepcopy(provisional)
    entry["id"] = source_id
    cap = CADENCE_CAPS.get(cadence, 60)
    entry["currency"] = {
        **(entry.get("currency") or {}),
        "as_of": today.isoformat(),
        "review_due": (today + timedelta(days=min(review_days, cap))).isoformat(),
        "cadence": cadence,
    }
    entry["ingest"] = {
        "tier": "canonical",
        "reviewed_by": reviewer,
        "reviewed_at": today.isoformat(),
        "review_note": "promoted from provisional after human review",
    }
    entry["license_evidence"] = {
        **(entry.get("license_evidence") or {}),
        "checked_at": today.isoformat(),
    }
    errors = validate_entry(entry)
    if errors:
        raise PromotionError("; ".join(errors))
    return {
        "source_id": source_id,
        "entry": entry,
        "actions": list(PROMOTION_ACTIONS),
        "reviewer": reviewer,
        "promoted_at": today.isoformat(),
    }


__all__ = ["PROMOTION_ACTIONS", "PromotionError", "promotion_draft"]
