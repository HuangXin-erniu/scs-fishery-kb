from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from ..parsers import Page as ParsedPage
from ..parsers import ParsedDocument, ParseError, parse_source

LEGACY_FORMATS = {"html", "docx", "ofd", "pdf", "doc", "xlsx", "xls"}
WEB_FORMATS = {"web", "txt"}


class LoaderError(RuntimeError):
    """Raised when no loader can turn a snapshot file into anchored text."""


@dataclass(frozen=True)
class LoadResult:
    parsed: ParsedDocument
    parser: str
    fallback: bool
    page_anchors: bool
    attempts: tuple[str, ...]


def available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def loader_plan(source_format: str, source_kind: str = "corpus") -> list[str]:
    """Return the ordered loader names for a format and channel.

    Registered HTML stays on the legacy parser because it already preserves
    article/section anchors. Web-card text prefers trafilatura, and PDF/DOCX use
    Docling only as a fallback when the legacy adapter fails.
    """
    fmt = (source_format or "").strip().lower()
    kind = (source_kind or "corpus").strip().lower()
    if kind == "web" or fmt in WEB_FORMATS:
        return ["trafilatura", "legacy"]
    if fmt in {"pdf", "docx"}:
        return ["legacy", "docling"]
    if fmt in LEGACY_FORMATS:
        return ["legacy"]
    return ["legacy"]


def _page(text: str) -> list[ParsedPage]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise LoaderError("loader.empty: no text extracted")
    return [ParsedPage(number=0, lines=lines)]


def _legacy(path: Path, source_format: str) -> ParsedDocument:
    fmt = source_format
    if fmt not in LEGACY_FORMATS and fmt in WEB_FORMATS:
        fmt = "html"
    return parse_source(path, fmt)


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise LoaderError(f"loader.encoding: cannot decode {path.name}")


def _trafilatura(path: Path) -> ParsedDocument:
    import trafilatura

    text = trafilatura.extract(
        _decode(path),
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if not text:
        raise LoaderError(f"loader.trafilatura.empty: {path.name}")
    return ParsedDocument(pages=_page(text), parser="trafilatura")


def _docling(path: Path) -> ParsedDocument:
    from docling.document_converter import DocumentConverter

    result = DocumentConverter().convert(str(path))
    document = result.document
    text = document.export_to_markdown()
    if not text:
        text = document.export_to_text()
    return ParsedDocument(pages=_page(text), parser="docling")


def load_document(
    path: Path,
    source_format: str,
    *,
    source_kind: str = "corpus",
) -> LoadResult:
    """Load one snapshot through the planned adapters, recording every attempt."""
    attempts: list[str] = []
    plan = loader_plan(source_format, source_kind)
    for index, name in enumerate(plan):
        attempts.append(name)
        try:
            if name == "legacy":
                parsed = _legacy(path, source_format)
                return LoadResult(
                    parsed=parsed,
                    parser=parsed.parser,
                    fallback=index > 0,
                    page_anchors=True,
                    attempts=tuple(attempts),
                )
            if name == "trafilatura":
                if not available("trafilatura"):
                    attempts.append("trafilatura.unavailable")
                    continue
                parsed = _trafilatura(path)
                return LoadResult(
                    parsed=parsed,
                    parser=parsed.parser,
                    fallback=index > 0,
                    page_anchors=False,
                    attempts=tuple(attempts),
                )
            if name == "docling":
                if not available("docling"):
                    attempts.append("docling.unavailable")
                    continue
                parsed = _docling(path)
                return LoadResult(
                    parsed=parsed,
                    parser=parsed.parser,
                    fallback=True,
                    page_anchors=False,
                    attempts=tuple(attempts),
                )
            raise LoaderError(f"loader.unknown: {name}")
        except (LoaderError, ParseError) as exc:
            attempts.append(f"{name}.error:{exc}")
            continue
    raise LoaderError(f"loader.failed: {'; '.join(attempts)}")


__all__ = [
    "LEGACY_FORMATS",
    "WEB_FORMATS",
    "LoadResult",
    "LoaderError",
    "available",
    "load_document",
    "loader_plan",
]
