"""Plain-language term mapping built on the approved terminology register."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..config import REPO_ROOT

DEFAULT_TERMS = REPO_ROOT / "configs" / "terms-plain.yaml"
MAX_PLAIN_CHARS = 80


class TermsError(RuntimeError):
    """Raised when the plain-term file is malformed."""


def load_terms_plain(path: Path | str = DEFAULT_TERMS) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise TermsError(f"plain terms not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    terms = data.get("terms") if isinstance(data, dict) else None
    if not isinstance(terms, list) or not terms:
        raise TermsError(f"plain terms are empty: {source}")
    seen: set[str] = set()
    for entry in terms:
        if not isinstance(entry, dict):
            raise TermsError("plain term is not a mapping")
        term_id = str(entry.get("term_id") or "")
        if not term_id or term_id in seen:
            raise TermsError(f"bad or duplicate term_id: {term_id!r}")
        seen.add(term_id)
        if not str(entry.get("official") or "").strip():
            raise TermsError(f"{term_id}: missing official name")
        plain = str(entry.get("plain") or "").strip()
        if not plain or len(plain) > MAX_PLAIN_CHARS:
            raise TermsError(f"{term_id}: plain text must be 1-{MAX_PLAIN_CHARS} chars")
        citations = entry.get("citations")
        if not isinstance(citations, list) or not citations:
            raise TermsError(f"{term_id}: no citation")
    return terms


__all__ = ["DEFAULT_TERMS", "MAX_PLAIN_CHARS", "TermsError", "load_terms_plain"]
