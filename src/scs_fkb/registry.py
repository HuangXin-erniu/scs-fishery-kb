from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .config import DEFAULT_CONFIG

LEVELS = frozenset({"national", "provincial", "municipal", "international"})
TIERS = frozenset({"A", "B", "C"})
SOURCE_CLASSES = frozenset({"normative", "official_statistics", "standard", "reference"})
BASES = frozenset({"publication", "edition", "announcement", "retrieval"})
CADENCES = frozenset(
    {
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "semiannual",
        "annual",
        "edition",
        "irregular",
        "static",
    }
)
CADENCE_CAPS = {
    "daily": 3,
    "weekly": 21,
    "monthly": 60,
    "quarterly": 150,
    "semiannual": 240,
    "annual": 400,
    "edition": 400,
    "irregular": 180,
    "static": 550,
}
LICENSES = frozenset({"public", "internal", "cc-by-nc-sa-3.0-igo"})
SENSITIVITIES = frozenset({"public", "internal", "restricted"})
CHANNELS = frozenset({"main", "collection", "statistics", "watch", "none"})
LIFECYCLES = frozenset({"active", "retired"})
REQUIRED = (
    "level",
    "authority_tier",
    "source_class",
    "currency",
    "retrieval",
    "lifecycle",
    "license",
    "sensitivity",
)


class RegistryError(RuntimeError):
    """Raised when a registry entry does not satisfy schema v3."""


def load_registry(path: Path | str = DEFAULT_CONFIG) -> dict[str, dict[str, Any]]:
    registry_path = Path(path)
    if not registry_path.is_file():
        raise RegistryError(f"registry not found: {registry_path}")
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    validate_registry(sources, path=registry_path)
    return {str(source["id"]): source for source in sources}  # type: ignore[union-attr]


def validate_registry(sources: Iterable[Any] | None, path: Path | None = None) -> None:
    where = f" in {path}" if path else ""
    if not isinstance(sources, list) or not sources:
        raise RegistryError(f"registry has no sources{where}")
    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(sources):
        if not isinstance(entry, dict):
            errors.append(f"entry #{index} is not a mapping")
            continue
        source_id = str(entry.get("id") or f"entry #{index}")
        if source_id in seen:
            errors.append(f"{source_id}: duplicate id")
        seen.add(source_id)
        errors.extend(validate_entry(entry))
    if errors:
        raise RegistryError("; ".join(errors))


def validate_entry(entry: dict[str, Any]) -> list[str]:
    source_id = str(entry.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in entry:
            errors.append(f"{source_id}: missing {key}")
    level = entry.get("level")
    if level is not None and level not in LEVELS:
        errors.append(f"{source_id}: level {level!r} not in {sorted(LEVELS)}")
    tier = entry.get("authority_tier")
    if tier is not None and tier not in TIERS:
        errors.append(f"{source_id}: authority_tier {tier!r} not in {sorted(TIERS)}")
    if tier == "C" and level != "municipal":
        errors.append(f"{source_id}: authority_tier C requires level municipal, not {level!r}")
    if tier in ("A", "B") and level == "municipal":
        errors.append(f"{source_id}: authority_tier {tier} cannot be municipal")
    license_value = entry.get("license")
    if license_value is not None and license_value not in LICENSES:
        errors.append(f"{source_id}: license {license_value!r} not in {sorted(LICENSES)}")
    sensitivity = entry.get("sensitivity")
    if sensitivity is not None and sensitivity not in SENSITIVITIES:
        errors.append(f"{source_id}: sensitivity {sensitivity!r} not in {sorted(SENSITIVITIES)}")
    if "validity" in entry:
        errors.append(f"{source_id}: validity is retired; use source_class and currency")
    source_class = entry.get("source_class")
    if source_class is not None and source_class not in SOURCE_CLASSES:
        errors.append(f"{source_id}: source_class {source_class!r} not in {sorted(SOURCE_CLASSES)}")
    errors.extend(_validate_currency(source_id, entry.get("currency")))
    errors.extend(_validate_retrieval(source_id, entry.get("retrieval")))
    lifecycle = entry.get("lifecycle")
    if lifecycle is not None and lifecycle not in LIFECYCLES:
        errors.append(f"{source_id}: lifecycle {lifecycle!r} not in {sorted(LIFECYCLES)}")
    if lifecycle == "retired":
        retirement = entry.get("retirement")
        if not isinstance(retirement, dict):
            errors.append(f"{source_id}: retired without a retirement block")
        else:
            for key in ("date", "reason", "decision_key"):
                if not retirement.get(key):
                    errors.append(f"{source_id}: retirement missing {key}")
    return errors


def _validate_currency(source_id: str, currency: Any) -> list[str]:
    if currency is None:
        return [f"{source_id}: currency is missing"]
    if not isinstance(currency, dict):
        return [f"{source_id}: currency is not a mapping"]
    errors: list[str] = []
    dates: dict[str, date] = {}
    for key in ("as_of", "review_due"):
        value = currency.get(key)
        if not value:
            errors.append(f"{source_id}: currency.{key} is empty")
            continue
        try:
            dates[key] = date.fromisoformat(str(value))
        except ValueError:
            errors.append(f"{source_id}: currency.{key} is not an ISO date")
    basis = currency.get("basis")
    if basis not in BASES:
        errors.append(f"{source_id}: currency.basis {basis!r} not in {sorted(BASES)}")
    cadence = currency.get("cadence")
    if cadence not in CADENCES:
        errors.append(f"{source_id}: currency.cadence {cadence!r} not in {sorted(CADENCES)}")
    if "as_of" in dates and "review_due" in dates and dates["review_due"] < dates["as_of"]:
        errors.append(f"{source_id}: currency.review_due is before as_of")
    elif cadence in CADENCE_CAPS and "as_of" in dates and "review_due" in dates:
        span = (dates["review_due"] - dates["as_of"]).days
        cap = CADENCE_CAPS[cadence]
        if span > cap:
            errors.append(
                f"{source_id}: review_due is {span} days after as_of, "
                f"beyond the {cap}-day cap for cadence {cadence}"
            )
    note = currency.get("note")
    if note is not None and not str(note).strip():
        errors.append(f"{source_id}: currency.note is empty")
    return errors


def _validate_retrieval(source_id: str, retrieval: Any) -> list[str]:
    if retrieval is None:
        return []
    if not isinstance(retrieval, dict):
        return [f"{source_id}: retrieval is not a mapping"]
    errors: list[str] = []
    channel = retrieval.get("channel")
    if channel not in CHANNELS:
        errors.append(f"{source_id}: retrieval.channel {channel!r} not in {sorted(CHANNELS)}")
    if not isinstance(retrieval.get("parseable"), bool):
        errors.append(f"{source_id}: retrieval.parseable is not a bool")
    if not retrieval.get("note"):
        errors.append(f"{source_id}: retrieval.note is empty")
    return errors


def check_currency(
    registry: dict[str, dict[str, Any]],
    *,
    today: date | None = None,
    grace_days: int = 30,
) -> dict[str, Any]:
    """Report active sources whose review date is older than the grace window."""
    current = today or date.today()
    if grace_days < 0:
        raise RegistryError("grace_days must not be negative")
    overdue: list[dict[str, Any]] = []
    errors: list[str] = []
    for source_id, entry in sorted(registry.items()):
        if entry.get("lifecycle") != "active":
            continue
        due_value = (entry.get("currency") or {}).get("review_due")
        try:
            due = date.fromisoformat(str(due_value))
        except ValueError:
            errors.append(f"{source_id}: review_due is not an ISO date")
            continue
        days = (current - due).days
        if days > grace_days:
            overdue.append({"id": source_id, "review_due": due.isoformat(), "days_overdue": days})
    return {
        "today": current.isoformat(),
        "grace_days": grace_days,
        "sources": len(registry),
        "overdue": overdue,
        "errors": errors,
    }


def select(
    sources: dict[str, dict[str, Any]],
    *,
    level: str | None = None,
    channel: str | None = None,
    lifecycle: str = "active",
) -> list[dict[str, Any]]:
    chosen = []
    for entry in sources.values():
        if lifecycle and entry.get("lifecycle") != lifecycle:
            continue
        if level and entry.get("level") != level:
            continue
        if channel and (entry.get("retrieval") or {}).get("channel") != channel:
            continue
        chosen.append(entry)
    return chosen


def validate_watch_coverage(
    registry: dict[str, dict[str, Any]], watch_sources: Iterable[Any]
) -> None:
    """Each active acquired national or provincial source names a watch entry or says why not."""
    watch_ids = {
        str(source["id"])
        for source in watch_sources
        if isinstance(source, dict) and source.get("id")
    }
    errors: list[str] = []
    for source_id, source in registry.items():
        if source.get("lifecycle") != "active" or source.get("status") != "acquired":
            continue
        if source.get("level") not in ("national", "provincial"):
            continue
        ref = source.get("watch_ref")
        note = source.get("watch_note")
        if ref:
            if str(ref) not in watch_ids:
                errors.append(f"{source_id}: watch_ref {ref!r} is not in the watch list")
        elif not (note and str(note).strip()):
            errors.append(f"{source_id}: has neither watch_ref nor watch_note")
    if errors:
        raise RegistryError("; ".join(errors))
