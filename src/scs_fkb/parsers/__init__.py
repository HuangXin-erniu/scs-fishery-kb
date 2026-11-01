from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import docx, html, ofd
from .base import Page, ParsedDocument, ParseError, UnsupportedFormatError

PARSERS: dict[str, Callable[[Path], ParsedDocument]] = {
    "html": html.parse,
    "docx": docx.parse,
    "ofd": ofd.parse,
}


def parse_source(path: Path, source_format: str) -> ParsedDocument:
    """Dispatch on the register format and return anchored page text."""
    key = (source_format or "").strip().lower()
    parser = PARSERS.get(key)
    if parser is None:
        raise UnsupportedFormatError(
            f"source.unsupported_format: no parser for {key or 'unknown'!r}"
        )
    return parser(path)


__all__ = [
    "PARSERS",
    "Page",
    "ParsedDocument",
    "ParseError",
    "UnsupportedFormatError",
    "parse_source",
]
