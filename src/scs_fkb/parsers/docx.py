from __future__ import annotations

import zipfile
from xml.etree import ElementTree as ET

from .base import Page, ParsedDocument, ParseError

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCUMENT_PART = "word/document.xml"


def _paragraph_lines(root: ET.Element) -> list[str]:
    lines: list[str] = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{WORD_NS}t" and node.text:
                parts.append(node.text)
            elif node.tag in (f"{WORD_NS}tab", f"{WORD_NS}br", f"{WORD_NS}cr"):
                parts.append(" ")
        text = " ".join("".join(parts).split())
        if text:
            lines.append(text)
    return lines


def parse(path) -> ParsedDocument:
    try:
        with zipfile.ZipFile(path) as archive:
            if DOCUMENT_PART not in archive.namelist():
                raise ParseError(f"source.invalid_docx: {path.name} has no {DOCUMENT_PART}")
            payload = archive.read(DOCUMENT_PART)
    except zipfile.BadZipFile as exc:
        raise ParseError(f"source.invalid_docx: {path.name} is not a zip archive") from exc

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ParseError(f"source.invalid_docx: {path.name} has malformed XML") from exc

    lines = _paragraph_lines(root)
    if not lines:
        raise ParseError(f"text.empty: no paragraphs in {path.name}")
    return ParsedDocument(pages=[Page(number=0, lines=lines)], parser="docx.v1")
