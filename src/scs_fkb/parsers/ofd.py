from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

from .base import Page, ParsedDocument, ParseError

PAGE_RE = re.compile(r"(?:^|/)Pages/Page_(\d+)/Content\.xml$")
SENTENCE_SPLIT = re.compile(r"(?<=[。；！？])")
TEXT_CODE_SUFFIX = "TextCode"


def _page_entries(archive: zipfile.ZipFile) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for name in archive.namelist():
        match = PAGE_RE.search(name)
        if match:
            entries.append((int(match.group(1)), name))
    entries.sort()
    return entries


def parse(path) -> ParsedDocument:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = _page_entries(archive)
            if not entries:
                raise ParseError(f"source.invalid_ofd: {path.name} has no page content")
            pages: list[Page] = []
            for index, name in entries:
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError as exc:
                    raise ParseError(f"source.invalid_ofd: malformed XML in {name}") from exc
                text = "".join(
                    element.text
                    for element in root.iter()
                    if element.tag.endswith(TEXT_CODE_SUFFIX) and element.text
                ).strip()
                lines = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
                if lines:
                    pages.append(Page(number=index + 1, lines=lines))
    except zipfile.BadZipFile as exc:
        raise ParseError(f"source.invalid_ofd: {path.name} is not a zip archive") from exc

    if not pages:
        raise ParseError(f"text.empty: no text in {path.name}")
    return ParsedDocument(pages=pages, parser="ofd.v1")
