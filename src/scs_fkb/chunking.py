from __future__ import annotations

from .extract import ARTICLE_RE, SECTION_RE
from .models import Chunk, Document
from .text import tokenize

MAX_FALLBACK_CHARS = 800


def _article_groups(text: str) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    section = ""
    parts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = ARTICLE_RE.match(stripped)
        if match:
            if parts:
                groups.append((section, parts))
            section = match.group(1)
            parts = [stripped]
        elif parts:
            parts.append(stripped)
    if parts:
        groups.append((section, parts))
    return groups


def _section_groups(text: str) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    section = ""
    parts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = SECTION_RE.match(stripped)
        if match:
            if parts:
                groups.append((section, parts))
            section = match.group(1)
            parts = [stripped]
        elif parts:
            parts.append(stripped)
    if parts:
        groups.append((section, parts))
    return groups


def _fallback_groups(text: str) -> list[tuple[str, list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    groups: list[tuple[str, list[str]]] = []
    parts: list[str] = []
    size = 0
    for line in lines:
        if parts and size + len(line) > MAX_FALLBACK_CHARS:
            groups.append(("", parts))
            parts = []
            size = 0
        parts.append(line)
        size += len(line)
    if parts:
        groups.append(("", parts))
    return groups


def chunk_document(document: Document, text: str) -> list[Chunk]:
    groups = _article_groups(text)
    if not groups:
        groups = _section_groups(text)
    if not groups:
        groups = _fallback_groups(text)

    chunks: list[Chunk] = []
    cursor = 0
    for index, (section, parts) in enumerate(groups):
        chunk_text = "\n".join(parts).strip()
        if not chunk_text:
            continue
        start = text.find(chunk_text, cursor)
        if start < 0:
            start = text.find(parts[0], cursor)
        if start < 0:
            start = cursor
        end = start + len(chunk_text)
        cursor = max(cursor, end)
        chunks.append(
            Chunk(
                chunk_id=f"{document.doc_id}-{index:04d}",
                doc_id=document.doc_id,
                source_id=document.source_id,
                page=1,
                section=section,
                text=chunk_text,
                token_count=len(tokenize(chunk_text)),
                char_start=start,
                char_end=end,
                sensitivity=document.sensitivity,
            )
        )
    return chunks
