"""Bounded evidence pack for the standard RAG arm.

The pack is the only context the answer model sees.  It caps the number of
items and characters, keeps the document/section/page label that the citation
validator resolves, and carries the metadata the answer contract needs
(authority tier, as-of, stale, provisional).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from ..models import Chunk, SearchHit

DEFAULT_MAX_CHARS = 12_000
DEFAULT_MAX_ITEMS = 8
DEFAULT_QUOTE_CHARS = 1_200


@dataclass(frozen=True)
class EvidenceItem:
    chunk: Chunk
    quote: str
    score: float
    rank: int
    title: str = ""
    trust: str = ""
    authority_tier: str = ""
    level: str = ""
    as_of: str = ""
    review_due: str = ""
    stale: bool = False
    provisional: bool = False

    @property
    def label(self) -> str:
        section = f" §{self.chunk.section}" if self.chunk.section else ""
        page = f" p.{self.chunk.page}" if self.chunk.page else ""
        return f"{self.chunk.doc_id}{section}{page}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "title": self.title,
            "section": self.chunk.section,
            "page": self.chunk.page,
            "quote": self.quote,
            "score": round(self.score, 6),
            "trust": self.trust,
            "authority_tier": self.authority_tier,
            "level": self.level,
            "as_of": self.as_of,
            "stale": self.stale,
            "provisional": self.provisional,
        }

    def to_model(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(frozen=True)
class EvidencePack:
    items: tuple[EvidenceItem, ...]
    text: str
    chars: int
    truncated: bool
    index_version: str = ""

    @property
    def hits(self) -> list[SearchHit]:
        return [SearchHit(chunk=item.chunk, score=item.score) for item in self.items]

    @property
    def by_label(self) -> dict[str, EvidenceItem]:
        return {item.label: item for item in self.items}

    @property
    def stale_docs(self) -> list[str]:
        return [item.chunk.doc_id for item in self.items if item.stale]

    @property
    def provisional(self) -> bool:
        return any(item.provisional for item in self.items)

    @property
    def as_of(self) -> str:
        values = [item.as_of for item in self.items if item.as_of]
        return max(values) if values else ""

    def to_models(self) -> list[dict[str, Any]]:
        return [item.to_model() for item in self.items]


def _iso_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _entry(registry: dict[str, dict[str, Any]] | None, doc_id: str) -> dict[str, Any]:
    if not registry:
        return {}
    return registry.get(doc_id) or {}


def _stale(entry: dict[str, Any], today: date) -> bool:
    currency = entry.get("currency") or {}
    review_due = _iso_date(currency.get("review_due"))
    if review_due is not None and review_due < today:
        return True
    effective = entry.get("effective") or {}
    until = _iso_date(effective.get("to"))
    return until is not None and until < today


def _provisional(entry: dict[str, Any], chunk: Chunk) -> bool:
    ingest = entry.get("ingest") or {}
    return str(ingest.get("tier") or "").lower() == "provisional" or (
        str(chunk.trust or "").lower() == "provisional"
    )


def _label(chunk: Chunk) -> str:
    section = f" §{chunk.section}" if chunk.section else ""
    page = f" p.{chunk.page}" if chunk.page else ""
    return f"{chunk.doc_id}{section}{page}"


def build_evidence_pack(
    hits: list[SearchHit],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_items: int = DEFAULT_MAX_ITEMS,
    quote_chars: int = DEFAULT_QUOTE_CHARS,
    registry: dict[str, dict[str, Any]] | None = None,
    index_version: str = "",
    today: date | None = None,
) -> EvidencePack:
    """Deduplicate hits, cap the pack and render the citation-labelled context."""
    current = today or date.today()
    items: list[EvidenceItem] = []
    seen: set[tuple[str, str, str]] = set()
    used = 0
    truncated = False
    for hit in hits:
        chunk = hit.chunk
        quote = " ".join(chunk.text.split())
        key = (chunk.doc_id, chunk.section, quote[:80])
        if key in seen:
            continue
        seen.add(key)
        if len(items) >= max_items:
            truncated = True
            break
        quote = quote[:quote_chars]
        entry = _entry(registry, chunk.doc_id)
        currency = entry.get("currency") or {}
        item = EvidenceItem(
            chunk=chunk,
            quote=quote,
            score=float(hit.score),
            rank=len(items),
            title=str(entry.get("title") or chunk.doc_id),
            trust=str(chunk.trust or entry.get("trust") or ""),
            authority_tier=str(chunk.authority_tier or entry.get("authority_tier") or ""),
            level=str(chunk.level or entry.get("level") or ""),
            as_of=str(currency.get("as_of") or chunk.retrieved_at[:10] or ""),
            review_due=str(currency.get("review_due") or ""),
            stale=_stale(entry, current),
            provisional=_provisional(entry, chunk),
        )
        block = f"[{_label(chunk)}] {item.quote}"
        if used + len(block) > max_chars:
            truncated = True
            break
        items.append(item)
        used += len(block)
    text = "\n\n".join(f"[{item.label}] {item.quote}" for item in items)
    return EvidencePack(
        items=tuple(items),
        text=text,
        chars=len(text),
        truncated=truncated,
        index_version=index_version,
    )


__all__ = [
    "DEFAULT_MAX_CHARS",
    "DEFAULT_MAX_ITEMS",
    "DEFAULT_QUOTE_CHARS",
    "EvidenceItem",
    "EvidencePack",
    "build_evidence_pack",
]
