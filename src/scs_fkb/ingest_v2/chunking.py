from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from ..chunking import MAX_FALLBACK_CHARS, chunk_document
from ..models import Chunk, Document
from ..parsers.base import Page
from ..patterns import ARTICLE_RE, SECTION_RE
from ..text import tokenize


@dataclass(frozen=True)
class Hierarchy:
    parents: list[Chunk]
    children: list[Chunk]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _trust(document: Document) -> str:
    tier = document.authority_tier or ""
    source_class = document.source_class or ""
    if tier in {"A", "B"} and source_class in {"normative", "official_statistics"}:
        return "authoritative"
    if tier in {"A", "B"}:
        return "standard"
    return "provisional"


def _section_path(page: int, section: str) -> str:
    prefix = f"p.{page}" if page else "document"
    return f"{prefix} / {section}" if section else prefix


def label_sections(chunks: list[Chunk]) -> list[Chunk]:
    """Give every chunk a section label so a citation can resolve.

    The article number in the chunk wins; a section heading in the first lines is
    next; the page label is the last resort. Chunks that already carry a section
    are returned unchanged.
    """
    labelled: list[Chunk] = []
    for chunk in chunks:
        if chunk.section.strip():
            labelled.append(chunk)
            continue
        head = chunk.text.strip()[:80]
        match = ARTICLE_RE.search(head) or SECTION_RE.search(head)
        if match:
            label = match.group(1)
        elif chunk.page:
            label = f"p.{chunk.page}"
        else:
            label = "正文"
        labelled.append(replace(chunk, section=label))
    return labelled


def hierarchical_chunks(
    document: Document,
    pages: list[Page],
    max_fallback_chars: int = MAX_FALLBACK_CHARS,
    *,
    kind: str = "corpus",
    review_due: str = "",
) -> Hierarchy:
    """Build parent sections from the proven child chunker.

    Children are exactly the v1 chunks, so page/section/article anchors are
    preserved by construction. A parent groups children that share a page and
    section; it is stored separately and is never the retrieval unit.
    """
    base = chunk_document(document, pages, max_fallback_chars)
    if not base:
        return Hierarchy(parents=[], children=[])
    base = label_sections(base)

    groups: dict[tuple[int, str], list[Chunk]] = {}
    for child in base:
        groups.setdefault((child.page, child.section), []).append(child)

    parents: list[Chunk] = []
    parent_ids: dict[tuple[int, str], str] = {}
    for (page, section), members in sorted(
        groups.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        parent_id = f"{document.doc_id}-P{page:04d}-{_digest(f'{page}|{section}')}"
        parent_ids[(page, section)] = parent_id
        text = "\n".join(member.text for member in members)
        parents.append(
            replace(
                members[0],
                chunk_id=parent_id,
                page=page,
                section=section,
                text=text,
                token_count=len(tokenize(text)),
                char_start=min(member.char_start for member in members),
                char_end=max(member.char_end for member in members),
                parent_id="",
                chunk_type="parent",
                section_path=_section_path(page, section),
                kind=kind,
                review_due=review_due,
            )
        )

    children: list[Chunk] = []
    for child in base:
        parent_id = parent_ids[(child.page, child.section)]
        children.append(
            replace(
                child,
                parent_id=parent_id,
                chunk_type="text",
                section_path=_section_path(child.page, child.section),
                version_id=document.version_id,
                snapshot_hash=document.snapshot_hash,
                authority_tier=document.authority_tier,
                ingest_tier=document.ingest_tier,
                level=document.level,
                jurisdiction=document.jurisdiction,
                license=document.license,
                effective_from=document.effective_from,
                effective_to=document.effective_to,
                source_class=document.source_class,
                trust=_trust(document),
                kind=kind,
                review_due=review_due,
            )
        )
    return Hierarchy(parents=parents, children=children)


__all__ = ["Hierarchy", "hierarchical_chunks"]
