from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import Page, ParsedDocument, ParseError

TOOL = "pdftotext"


def parse(path: Path) -> ParsedDocument:
    """Extract one Page per PDF page through the local poppler tool."""
    if shutil.which(TOOL) is None:
        raise ParseError(f"tool.missing: {TOOL} (poppler) is required to read PDF sources")
    result = subprocess.run(
        [TOOL, "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or "").strip().splitlines()
        detail = message[0][:200] if message else f"exit {result.returncode}"
        raise ParseError(f"source.invalid_pdf: {path.name}: {detail}")

    pages: list[Page] = []
    for index, block in enumerate(result.stdout.split("\f")):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            pages.append(Page(number=index + 1, lines=lines))
    if not pages:
        raise ParseError(f"text.empty: no text in {path.name}")
    return ParsedDocument(pages=pages, parser="pdf.v1")
