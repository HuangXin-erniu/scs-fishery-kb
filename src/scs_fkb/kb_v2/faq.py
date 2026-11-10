"""Sourced FAQ: every answer is a short approved fact value with a citation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ..config import REPO_ROOT

DEFAULT_FAQ = REPO_ROOT / "configs" / "faq.yaml"
MAX_ANSWER_CHARS = 200
FAQ_ID = re.compile(r"FAQ-\d{3}")


class KbError(RuntimeError):
    """Raised when a knowledge-layer file is malformed."""


def load_faq(path: Path | str = DEFAULT_FAQ) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise KbError(f"FAQ not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise KbError(f"FAQ has no entries: {source}")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise KbError("FAQ entry is not a mapping")
        identifier = str(entry.get("id") or "")
        if not FAQ_ID.fullmatch(identifier):
            raise KbError(f"bad FAQ id: {identifier!r}")
        if identifier in seen:
            raise KbError(f"duplicate FAQ id: {identifier}")
        seen.add(identifier)
        for key in ("question", "answer", "topic"):
            if not str(entry.get(key) or "").strip():
                raise KbError(f"{identifier}: missing {key}")
        if len(str(entry["answer"])) > MAX_ANSWER_CHARS:
            raise KbError(f"{identifier}: answer is longer than {MAX_ANSWER_CHARS} chars")
        citations = entry.get("citations")
        if not isinstance(citations, list) or not citations:
            raise KbError(f"{identifier}: no citations")
    return entries


def search_faq(entries: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    needle = str(query or "").strip().lower()
    if not needle:
        return entries
    hits: list[dict[str, Any]] = []
    for entry in entries:
        haystack = " ".join(
            [
                str(entry.get("question") or ""),
                str(entry.get("answer") or ""),
                " ".join(str(item) for item in entry.get("variants") or []),
            ]
        ).lower()
        if needle in haystack:
            hits.append(entry)
    return hits


__all__ = ["DEFAULT_FAQ", "KbError", "load_faq", "search_faq"]
