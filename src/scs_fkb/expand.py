from __future__ import annotations

from pathlib import Path

import yaml

from .config import REPO_ROOT

DEFAULT_BRIDGE = REPO_ROOT / "configs" / "glossary-bridge.yaml"


class BridgeError(RuntimeError):
    """Raised when the terminology bridge is missing or malformed."""


def load_bridge(path: Path | None = None) -> list[dict[str, object]]:
    bridge_path = Path(path) if path else DEFAULT_BRIDGE
    if not bridge_path.is_file():
        raise BridgeError(f"glossary bridge not found: {bridge_path}")
    data = yaml.safe_load(bridge_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise BridgeError(f"unsupported bridge schema in {bridge_path}")
    terms = data.get("terms")
    if not isinstance(terms, list) or not terms:
        raise BridgeError(f"bridge lists no terms: {bridge_path}")
    entries: list[dict[str, object]] = []
    for entry in terms:
        if not isinstance(entry, dict):
            raise BridgeError("bridge term must be a mapping")
        zh = str(entry.get("zh") or "").strip()
        en = entry.get("en")
        if not zh or not isinstance(en, list) or not en:
            raise BridgeError(f"bridge term is incomplete: {entry}")
        entries.append({"zh": zh, "en": [str(item) for item in en]})
    return entries


def concepts_for(text: str, bridge: list[dict[str, object]] | None = None) -> list[str]:
    """Return the English concepts of the longest matching Chinese terms."""
    entries = bridge if bridge is not None else load_bridge()
    ordered = sorted(entries, key=lambda entry: len(str(entry["zh"])), reverse=True)
    consumed: list[tuple[int, int]] = []
    matched: list[dict[str, object]] = []
    for entry in ordered:
        zh = str(entry["zh"])
        start = text.find(zh)
        while start >= 0:
            span = (start, start + len(zh))
            overlaps = any(span[0] < end and start_span < span[1] for start_span, end in consumed)
            if not overlaps:
                consumed.append(span)
                matched.append(entry)
                break
            start = text.find(zh, start + 1)
    ordered_matches = sorted(matched, key=lambda entry: text.find(str(entry["zh"])))
    concepts: list[str] = []
    for entry in ordered_matches:
        for concept in entry["en"]:  # type: ignore[union-attr]
            if concept not in concepts:
                concepts.append(concept)
    return concepts


def expanded_query(text: str, concepts: list[str]) -> str:
    if not concepts:
        return text
    return f"{text} {' '.join(concepts)}"
