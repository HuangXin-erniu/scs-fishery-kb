from __future__ import annotations

from pathlib import Path

import yaml

from .config import REPO_ROOT

DEFAULT_LEXICON = REPO_ROOT / "configs" / "lexicon.yaml"


class LexiconError(RuntimeError):
    """Raised when the synonym lexicon is missing or malformed."""


def load_lexicon(path: Path | None = None) -> list[dict[str, object]]:
    lexicon_path = Path(path) if path else DEFAULT_LEXICON
    if not lexicon_path.is_file():
        raise LexiconError(f"lexicon not found: {lexicon_path}")
    data = yaml.safe_load(lexicon_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise LexiconError(f"unsupported lexicon schema in {lexicon_path}")
    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        raise LexiconError(f"lexicon lists no groups: {lexicon_path}")
    entries: list[dict[str, object]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise LexiconError("lexicon group must be a mapping")
        term = str(group.get("term") or "").strip()
        variants = group.get("variants")
        if not term or not isinstance(variants, list) or not variants:
            raise LexiconError(f"lexicon group is incomplete: {group}")
        entries.append({"term": term, "variants": [str(item) for item in variants]})
    return entries


def expand_query(text: str, groups: list[dict[str, object]] | None) -> str:
    """Append the variants of the longest matching terms, once each."""
    if not groups:
        return text
    ordered = sorted(groups, key=lambda group: len(str(group["term"])), reverse=True)
    consumed: list[tuple[int, int]] = []
    additions: list[str] = []
    for group in ordered:
        term = str(group["term"])
        start = text.find(term)
        while start >= 0:
            span = (start, start + len(term))
            overlaps = any(span[0] < end and left < span[1] for left, end in consumed)
            if not overlaps:
                consumed.append(span)
                for variant in group["variants"]:  # type: ignore[union-attr]
                    if variant not in additions:
                        additions.append(variant)
                break
            start = text.find(term, start + 1)
    if not additions:
        return text
    return f"{text} {' '.join(additions)}"
