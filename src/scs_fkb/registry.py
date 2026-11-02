from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from .config import DEFAULT_CONFIG

LEVELS = frozenset({"national", "provincial", "municipal", "international"})
TIERS = frozenset({"A", "B", "C"})
VALIDITY = frozenset({"in_force", "superseded", "repealed", "unknown", "not_applicable"})
CHANNELS = frozenset({"main", "collection", "statistics", "watch", "none"})
LIFECYCLES = frozenset({"active", "retired"})
REQUIRED = ("level", "authority_tier", "validity", "retrieval", "lifecycle")


class RegistryError(RuntimeError):
    """Raised when a registry entry does not satisfy schema v2."""


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
    errors.extend(_validate_validity(source_id, entry.get("validity")))
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


def _validate_validity(source_id: str, validity: Any) -> list[str]:
    if validity is None:
        return []
    if not isinstance(validity, dict):
        return [f"{source_id}: validity is not a mapping"]
    errors: list[str] = []
    status = validity.get("status")
    if status not in VALIDITY:
        errors.append(f"{source_id}: validity.status {status!r} not in {sorted(VALIDITY)}")
    for key in ("as_of", "note"):
        if not validity.get(key):
            errors.append(f"{source_id}: validity.{key} is empty")
    for key in ("supersedes", "superseded_by"):
        value = validity.get(key)
        if value is not None and not isinstance(value, list):
            errors.append(f"{source_id}: validity.{key} is not a list")
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
