from __future__ import annotations

import re

from .models import Chunk, Document
from .parsers.base import Page
from .patterns import ARTICLE_RE, SECTION_RE
from .text import tokenize

MAX_FALLBACK_CHARS = 800
MIN_CHUNK_CHARS = 10

# Table-of-contents lines: dot leaders followed by a page number. They carry no
# answerable content and would otherwise become one tiny section chunk each.
TOC_LINE_RE = re.compile(r"\.{4,}\s*\d+\s*$")


def _content_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and not TOC_LINE_RE.search(line)]


def _article_groups(lines: list[str]) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    section = ""
    parts: list[str] = []
    for line in lines:
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


def _section_groups(lines: list[str]) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    section = ""
    parts: list[str] = []
    for line in lines:
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


def _fallback_groups(lines: list[str], max_chars: int) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    parts: list[str] = []
    size = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if parts and size + len(stripped) > max_chars:
            groups.append(("", parts))
            parts = []
            size = 0
        parts.append(stripped)
        size += len(stripped)
    if parts:
        groups.append(("", parts))
    return groups


def _page_groups(page: Page, max_chars: int) -> list[tuple[str, list[str]]]:
    lines = _content_lines(page.lines)
    groups = _article_groups(lines)
    if not groups:
        groups = _section_groups(lines)
    if not groups:
        groups = _fallback_groups(lines, max_chars)
    return groups


def chunk_document(
    document: Document,
    pages: list[Page],
    max_fallback_chars: int = MAX_FALLBACK_CHARS,
) -> list[Chunk]:
    """Split each page by article, then section, then a fixed-size fallback.

    Every chunk keeps the page number of the page it starts on (0 when the
    source is unpaginated), so a citation can resolve to either
    ``[doc p.N §section]`` or ``[doc §section]``.
    """
    chunks: list[Chunk] = []
    offset = 0
    index = 0
    for page in pages:
        page_text = page.text
        for section, parts in _page_groups(page, max_fallback_chars):
            chunk_text = "\n".join(parts).strip()
            if len(chunk_text) < MIN_CHUNK_CHARS:
                continue
            start = page_text.find(chunk_text)
            if start < 0:
                start = page_text.find(parts[0])
            if start < 0:
                start = 0
            end = start + len(chunk_text)
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}-{index:04d}",
                    doc_id=document.doc_id,
                    source_id=document.source_id,
                    page=page.number,
                    section=section,
                    text=chunk_text,
                    token_count=len(tokenize(chunk_text)),
                    char_start=offset + start,
                    char_end=offset + end,
                    sensitivity=document.sensitivity,
                )
            )
            index += 1
        offset += len(page_text) + 1
    return chunks
