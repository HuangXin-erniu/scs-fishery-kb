from __future__ import annotations

from dataclasses import dataclass


class ParseError(RuntimeError):
    """Raised when a source file cannot be turned into anchored text."""


class UnsupportedFormatError(ParseError):
    """Raised when the register names a format no parser handles."""


@dataclass(frozen=True)
class Page:
    """One page of extracted text.

    ``number`` is one-based for paginated sources and 0 when the source has no
    pages of its own (HTML pages and DOCX files carry article anchors instead).
    """

    number: int
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[Page]
    parser: str

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages)
