from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from .config import REPO_ROOT

DEFAULT_CANDIDATES = REPO_ROOT / "configs" / "candidates.yaml"
CANDIDATE_ID = re.compile(r"CAND-\d{4}-\d{3}")
STATUSES = frozenset({"open", "accepted", "rejected", "expired"})
REASONS = frozenset({"changed", "gap", "new", "supersede"})
TIERS = frozenset({"A", "B", "C"})
CLASSES = frozenset({"normative", "official_statistics", "standard", "reference"})
REQUIRED = (
    "id",
    "title",
    "url",
    "publisher",
    "proposed_tier",
    "reason",
    "first_seen",
    "expires_at",
    "status",
)
OPEN_DUE_DAYS = 90
DEFAULT_TTL_DAYS = 180


class CandidateError(RuntimeError):
    """Raised when a candidate file or entry is malformed."""


def _iso(value: Any, field: str, candidate_id: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise CandidateError(f"{candidate_id}: {field} is not an ISO date") from exc


def normalize_url(url: str) -> str:
    return str(url).strip().rstrip("/")


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
    if not isinstance(candidate, dict):
        return ["candidate is not a mapping"]
    candidate_id = str(candidate.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in candidate:
            errors.append(f"{candidate_id}: missing {key}")
    if not CANDIDATE_ID.fullmatch(candidate_id):
        errors.append(f"{candidate_id}: id must match CAND-YYYY-NNN")
    for key in ("title", "publisher"):
        if key in candidate and not str(candidate.get(key) or "").strip():
            errors.append(f"{candidate_id}: {key} is empty")
    url = str(candidate.get("url") or "")
    if not url.startswith(("http://", "https://")):
        errors.append(f"{candidate_id}: url must start with http:// or https://")
    tier = candidate.get("proposed_tier")
    if tier not in TIERS:
        errors.append(f"{candidate_id}: proposed_tier {tier!r} not in {sorted(TIERS)}")
    proposed_class = candidate.get("proposed_class")
    if proposed_class is not None and proposed_class not in CLASSES:
        errors.append(f"{candidate_id}: proposed_class {proposed_class!r} not in {sorted(CLASSES)}")
    reason = candidate.get("reason")
    if reason not in REASONS:
        errors.append(f"{candidate_id}: reason {reason!r} not in {sorted(REASONS)}")
    status = candidate.get("status")
    if status not in STATUSES:
        errors.append(f"{candidate_id}: status {status!r} not in {sorted(STATUSES)}")
    try:
        first_seen = _iso(candidate.get("first_seen"), "first_seen", candidate_id)
        expires_at = _iso(candidate.get("expires_at"), "expires_at", candidate_id)
        if expires_at < first_seen:
            errors.append(f"{candidate_id}: expires_at is before first_seen")
    except CandidateError as exc:
        errors.append(str(exc))
    if status == "accepted" and not str(candidate.get("source_id") or "").strip():
        errors.append(f"{candidate_id}: accepted candidate needs source_id")
    if status == "rejected" and not str(candidate.get("note") or "").strip():
        errors.append(f"{candidate_id}: rejected candidate needs a note")
    return errors


def load_candidates(path: Path | str = DEFAULT_CANDIDATES) -> list[dict[str, Any]]:
    candidate_path = Path(path)
    if not candidate_path.is_file():
        raise CandidateError(f"candidate register not found: {candidate_path}")
    data = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise CandidateError(f"unsupported candidate schema: {candidate_path}")
    items = data.get("candidates")
    if not isinstance(items, list):
        raise CandidateError(f"candidates is not a list: {candidate_path}")
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{candidate_path}: entry is not a mapping")
            continue
        candidate_id = str(item.get("id") or "<unknown>")
        errors.extend(validate_candidate(item))
        if candidate_id in seen_ids:
            errors.append(f"{candidate_id}: duplicate id")
        seen_ids.add(candidate_id)
        normalized = normalize_url(str(item.get("url") or ""))
        if normalized in seen_urls:
            errors.append(f"{candidate_id}: duplicate url {normalized}")
        seen_urls.add(normalized)
    if errors:
        raise CandidateError("; ".join(errors))
    return items


def check_candidates(
    path: Path | str = DEFAULT_CANDIDATES,
    *,
    today: date | None = None,
    registry_ids: set[str] | None = None,
    due_days: int = OPEN_DUE_DAYS,
) -> dict[str, Any]:
    """Report open candidates that are due, expired, or point at a missing source."""
    current = today or date.today()
    items = load_candidates(path)
    due: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    errors: list[str] = []
    counts: dict[str, int] = {status: 0 for status in sorted(STATUSES)}
    for item in items:
        counts[str(item["status"])] = counts.get(str(item["status"]), 0) + 1
        source_id = str(item.get("source_id") or "")
        if source_id and registry_ids is not None and source_id not in registry_ids:
            errors.append(f"{item['id']}: source_id {source_id!r} is not in the registry")
        if item["status"] != "open":
            continue
        first_seen = date.fromisoformat(str(item["first_seen"]))
        expires_at = date.fromisoformat(str(item["expires_at"]))
        if expires_at < current:
            expired.append(
                {
                    "id": str(item["id"]),
                    "expires_at": expires_at.isoformat(),
                    "days_past": (current - expires_at).days,
                }
            )
        elif (current - first_seen).days > due_days:
            due.append(
                {
                    "id": str(item["id"]),
                    "first_seen": first_seen.isoformat(),
                    "days_open": (current - first_seen).days,
                }
            )
    return {
        "path": str(path),
        "today": current.isoformat(),
        "total": len(items),
        "counts": counts,
        "due": due,
        "expired": expired,
        "errors": errors,
    }


def propose_from_watch(
    report: dict[str, Any],
    existing: list[dict[str, Any]],
    *,
    today: date | None = None,
    ttl_days: int = DEFAULT_TTL_DAYS,
) -> list[dict[str, Any]]:
    """Turn changed or unbaselined watch entries into candidate proposals.

    The function is pure: it never writes the register and never ingests a page.
    """
    current = today or date.today()
    existing_urls = {normalize_url(str(item.get("url") or "")) for item in existing}
    active_refs = {
        str(item.get("watch_ref"))
        for item in existing
        if item.get("watch_ref") and item.get("status") in {"open", "accepted"}
    }
    year = current.year
    numeric = [
        int(str(item["id"]).rsplit("-", 1)[1])
        for item in existing
        if CANDIDATE_ID.fullmatch(str(item.get("id") or ""))
        and str(item["id"]).startswith(f"CAND-{year}-")
    ]
    sequence = max(numeric or [0])
    proposals: list[dict[str, Any]] = []
    for result in report.get("results") or []:
        if not isinstance(result, dict):
            continue
        status = result.get("status")
        if status not in {"changed", "unbaselined"}:
            continue
        watch_ref = str(result.get("id") or "")
        url = str(result.get("url") or "")
        if not watch_ref or not url:
            continue
        if watch_ref in active_refs or normalize_url(url) in existing_urls:
            continue
        sequence += 1
        proposals.append(
            {
                "id": f"CAND-{year}-{sequence:03d}",
                "title": str(result.get("title") or watch_ref),
                "url": url,
                "publisher": str(result.get("publisher") or "unknown"),
                "proposed_tier": result.get("authority"),
                "proposed_class": None,
                "reason": "changed" if status == "changed" else "new",
                "watch_ref": watch_ref,
                "first_seen": current.isoformat(),
                "expires_at": (current + timedelta(days=ttl_days)).isoformat(),
                "status": "open",
                "decision_key": None,
                "source_id": None,
                "note": f"Watch reported {status}; review before registering.",
            }
        )
        existing_urls.add(normalize_url(url))
        active_refs.add(watch_ref)
    return proposals
