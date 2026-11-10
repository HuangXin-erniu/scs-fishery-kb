"""What changed: recent source dates, supersessions and upcoming reviews."""

from __future__ import annotations

from datetime import date
from typing import Any

WINDOW_DAYS = 120
UPCOMING_DAYS = 90


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def build_updates(
    registry: dict[str, dict[str, Any]],
    *,
    today: date | None = None,
    limit: int = 12,
) -> dict[str, list[dict[str, Any]]]:
    current = today or date.today()
    recent: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []
    for source_id, entry in registry.items():
        if entry.get("lifecycle") != "active":
            continue
        title = str(entry.get("title") or source_id)
        currency = entry.get("currency") or {}
        as_of = _date(currency.get("as_of"))
        if as_of is not None and (current - as_of).days <= WINDOW_DAYS:
            recent.append(
                {
                    "id": source_id,
                    "title": title,
                    "as_of": as_of.isoformat(),
                    "tier": str(entry.get("authority_tier") or ""),
                }
            )
        replaces = entry.get("supersedes")
        if replaces:
            superseded.append(
                {
                    "id": source_id,
                    "title": title,
                    "supersedes": replaces if isinstance(replaces, str) else ", ".join(replaces),
                    "as_of": as_of.isoformat() if as_of else "",
                }
            )
        due = _date(currency.get("review_due"))
        if due is not None and 0 <= (due - current).days <= UPCOMING_DAYS:
            upcoming.append({"id": source_id, "title": title, "review_due": due.isoformat()})
    recent.sort(key=lambda row: row["as_of"], reverse=True)
    upcoming.sort(key=lambda row: row["review_due"])
    return {
        "recent": recent[:limit],
        "superseded": superseded[:limit],
        "upcoming": upcoming[:limit],
    }


__all__ = ["build_updates"]
