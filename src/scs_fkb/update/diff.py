"""Diff watch results against the recorded baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CHANGE_STATUSES = frozenset({"changed", "unbaselined"})


@dataclass(frozen=True)
class Change:
    watch_id: str
    title: str
    url: str
    publisher: str
    authority: str
    status: str
    sha256: str = ""
    baseline_sha256: str = ""
    http_status: int | None = None
    error: str = ""
    text_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "watch_id": self.watch_id,
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "authority": self.authority,
            "status": self.status,
            "sha256": self.sha256,
            "baseline_sha256": self.baseline_sha256,
            "http_status": self.http_status,
            "error": self.error,
            "text_chars": self.text_chars,
        }


def changes_from_watch(
    report: dict[str, Any],
    baseline: dict[str, str] | None = None,
) -> list[Change]:
    """Return only changed or unbaselined watch rows, in stable order."""
    rows = report.get("results") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return []
    recorded = baseline or {}
    changes: list[Change] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "")
        if status not in CHANGE_STATUSES:
            continue
        watch_id = str(row.get("id") or "")
        changes.append(
            Change(
                watch_id=watch_id,
                title=str(row.get("title") or watch_id),
                url=str(row.get("url") or ""),
                publisher=str(row.get("publisher") or ""),
                authority=str(row.get("authority") or ""),
                status=status,
                sha256=str(row.get("sha256") or ""),
                baseline_sha256=str(recorded.get(watch_id) or ""),
                http_status=row.get("http_status"),
                error=str(row.get("error") or ""),
                text_chars=int(row.get("text_chars") or 0),
            )
        )
    return sorted(changes, key=lambda item: item.watch_id)


__all__ = ["CHANGE_STATUSES", "Change", "changes_from_watch"]
