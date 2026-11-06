from __future__ import annotations

import copy
import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .config import DEFAULT_CONFIG

SOURCE_RECORD_SCHEMA = 4
LEGACY_SOURCE_RECORD_SCHEMA = 3
LEVELS = frozenset({"national", "provincial", "municipal", "international", "non_official"})
TIERS = frozenset({"A", "B", "C", "D"})
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
LICENSES = frozenset({"public", "internal", "licensed", "cc-by-nc-sa-3.0-igo"})
SENSITIVITIES = frozenset({"public", "internal", "restricted"})
CHANNELS = frozenset({"main", "collection", "statistics", "watch", "web", "local", "none"})
LIFECYCLES = frozenset({"active", "retired"})
PROVENANCE_KEYS = frozenset(
    {
        "url",
        "document_no",
        "published_at",
        "retrieved_at",
        "sha256",
        "bytes",
        "mime",
        "snapshot_path",
    }
)
EFFECTIVE_KEYS = frozenset({"from", "to"})
QUALITY_KEYS = frozenset({"text_layer", "anchors", "tables", "ocr", "quarantine_reason"})
HASH_RE = re.compile(r"[0-9a-f]{64}")
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
    """Raised when a registry entry does not satisfy source schema v4."""


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a v4-shaped copy of a source entry, deriving v3 defaults.

    The register file keeps the compact v3 shape until a source is next edited.
    The loader always presents the v4 shape so callers do not need to branch on
    ``source_record_schema``. Derivation never overwrites an explicit value.
    """
    source = copy.deepcopy(entry)
    schema = source.get("source_record_schema", LEGACY_SOURCE_RECORD_SCHEMA)
    if schema in {LEGACY_SOURCE_RECORD_SCHEMA, SOURCE_RECORD_SCHEMA}:
        source["source_record_schema"] = SOURCE_RECORD_SCHEMA

    provenance = source.get("provenance")
    if isinstance(provenance, dict):
        provenance = dict(provenance)
        if source.get("hash") and not provenance.get("sha256"):
            provenance["sha256"] = source.get("hash")
        if source.get("location") and not provenance.get("snapshot_path"):
            provenance["snapshot_path"] = source.get("location")
        for key in PROVENANCE_KEYS:
            provenance.setdefault(key, None)
        source["provenance"] = provenance
    elif provenance is None:
        source["provenance"] = {
            "sha256": source.get("hash"),
            "snapshot_path": source.get("location"),
        }
        for key in PROVENANCE_KEYS:
            source["provenance"].setdefault(key, None)

    effective = source.get("effective")
    if isinstance(effective, dict):
        effective = dict(effective)
        for key in EFFECTIVE_KEYS:
            effective.setdefault(key, None)
        source["effective"] = effective
    elif effective is None:
        source["effective"] = {"from": None, "to": None}

    quality = source.get("quality")
    if isinstance(quality, dict):
        quality = dict(quality)
        for key in QUALITY_KEYS:
            quality.setdefault(key, None)
        source["quality"] = quality
    elif quality is None:
        source["quality"] = dict.fromkeys(QUALITY_KEYS)

    source.setdefault("license_note", None)
    source.setdefault("supersedes", None)
    source.setdefault("superseded_by", None)
    return source


def load_registry(path: Path | str = DEFAULT_CONFIG) -> dict[str, dict[str, Any]]:
    registry_path = Path(path)
    if not registry_path.is_file():
        raise RegistryError(f"registry not found: {registry_path}")
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    validate_registry(sources, path=registry_path)
    return {str(source["id"]): normalize_entry(source) for source in sources}  # type: ignore[union-attr]


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
    entry = normalize_entry(entry)
    source_id = str(entry.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in entry:
            errors.append(f"{source_id}: missing {key}")
    schema = entry.get("source_record_schema")
    if schema != SOURCE_RECORD_SCHEMA:
        errors.append(
            f"{source_id}: source_record_schema {schema!r} is not supported; "
            f"expected {SOURCE_RECORD_SCHEMA}"
        )
    level = entry.get("level")
    if level is not None and level not in LEVELS:
        errors.append(f"{source_id}: level {level!r} not in {sorted(LEVELS)}")
    tier = entry.get("authority_tier")
    if tier is not None and tier not in TIERS:
        errors.append(f"{source_id}: authority_tier {tier!r} not in {sorted(TIERS)}")
    if tier == "C" and level != "municipal":
        errors.append(f"{source_id}: authority_tier C requires level municipal, not {level!r}")
    if tier == "D" and level != "non_official":
        errors.append(f"{source_id}: authority_tier D requires level non_official, not {level!r}")
    if tier in ("A", "B") and level in ("municipal", "non_official"):
        errors.append(f"{source_id}: authority_tier {tier} cannot be {level}")
    if level == "non_official" and tier != "D":
        errors.append(f"{source_id}: level non_official requires authority_tier D, not {tier!r}")
    license_value = entry.get("license")
    if license_value is not None and license_value not in LICENSES:
        errors.append(f"{source_id}: license {license_value!r} not in {sorted(LICENSES)}")
    if license_value == "licensed" and not str(entry.get("license_note") or "").strip():
        errors.append(f"{source_id}: license licensed requires license_note")
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
    errors.extend(_validate_provenance(source_id, entry.get("provenance"), entry.get("hash")))
    errors.extend(_validate_effective(source_id, entry.get("effective")))
    errors.extend(_validate_quality(source_id, entry.get("quality")))
    errors.extend(_validate_supersession(source_id, entry))
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


def _iso_date(source_id: str, field: str, value: Any) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _validate_provenance(source_id: str, provenance: Any, source_hash: Any) -> list[str]:
    if not isinstance(provenance, dict):
        return [f"{source_id}: provenance is not a mapping"]
    errors: list[str] = []
    digest = provenance.get("sha256")
    if digest is not None:
        if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
            errors.append(f"{source_id}: provenance.sha256 is not a 64-character hex digest")
        elif source_hash and str(source_hash) != digest:
            errors.append(f"{source_id}: provenance.sha256 does not match hash")
    snapshot = provenance.get("snapshot_path")
    if snapshot is not None:
        if not isinstance(snapshot, str) or not snapshot.strip():
            errors.append(f"{source_id}: provenance.snapshot_path is empty")
        else:
            path = Path(snapshot)
            if path.is_absolute() or ".." in path.parts:
                errors.append(
                    f"{source_id}: provenance.snapshot_path must stay under the data root"
                )
    url = provenance.get("url")
    if url is not None and not str(url).startswith(("http://", "https://")):
        errors.append(f"{source_id}: provenance.url must start with http:// or https://")
    for key in ("document_no", "mime"):
        value = provenance.get(key)
        if value is not None and not str(value).strip():
            errors.append(f"{source_id}: provenance.{key} is empty")
    size = provenance.get("bytes")
    if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size < 0):
        errors.append(f"{source_id}: provenance.bytes must be a non-negative integer")
    for key in ("published_at", "retrieved_at"):
        value = provenance.get(key)
        if value is not None and _iso_date(source_id, f"provenance.{key}", value) is None:
            errors.append(f"{source_id}: provenance.{key} is not an ISO date")
    return errors


def _validate_effective(source_id: str, effective: Any) -> list[str]:
    if not isinstance(effective, dict):
        return [f"{source_id}: effective is not a mapping"]
    errors: list[str] = []
    start = _iso_date(source_id, "effective.from", effective.get("from"))
    end = _iso_date(source_id, "effective.to", effective.get("to"))
    if effective.get("from") is not None and start is None:
        errors.append(f"{source_id}: effective.from is not an ISO date")
    if effective.get("to") is not None and end is None:
        errors.append(f"{source_id}: effective.to is not an ISO date")
    if start is not None and end is not None and end < start:
        errors.append(f"{source_id}: effective.to is before effective.from")
    return errors


def _validate_quality(source_id: str, quality: Any) -> list[str]:
    if not isinstance(quality, dict):
        return [f"{source_id}: quality is not a mapping"]
    errors: list[str] = []
    for key in ("text_layer", "ocr"):
        value = quality.get(key)
        if value is not None and not isinstance(value, bool):
            errors.append(f"{source_id}: quality.{key} must be a boolean or null")
    for key in ("anchors", "tables"):
        value = quality.get(key)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            errors.append(f"{source_id}: quality.{key} must be a non-negative integer or null")
    note = quality.get("quarantine_reason")
    if note is not None and not str(note).strip():
        errors.append(f"{source_id}: quality.quarantine_reason is empty")
    return errors


def _validate_supersession(source_id: str, entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    supersedes = entry.get("supersedes")
    superseded_by = entry.get("superseded_by")
    for key, value in (("supersedes", supersedes), ("superseded_by", superseded_by)):
        if value is not None and not str(value).strip():
            errors.append(f"{source_id}: {key} is empty")
        if value is not None and str(value) == source_id:
            errors.append(f"{source_id}: {key} must not point at the entry itself")
    if supersedes is not None and superseded_by is not None and supersedes == superseded_by:
        errors.append(f"{source_id}: supersedes and superseded_by must differ")
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
