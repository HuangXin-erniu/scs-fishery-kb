from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import Page, ParsedDocument, ParseError

TOOL = "textutil"


def parse(path: Path) -> ParsedDocument:
    """Extract text from a legacy .doc file through the macOS textutil tool."""
    if shutil.which(TOOL) is None:
        raise ParseError(f"tool.missing: {TOOL} is required to read legacy DOC sources")
    result = subprocess.run(
        [TOOL, "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or "").strip().splitlines()
        detail = message[0][:200] if message else f"exit {result.returncode}"
        raise ParseError(f"source.invalid_doc: {path.name}: {detail}")

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise ParseError(f"text.empty: no text in {path.name}")
    return ParsedDocument(pages=[Page(number=0, lines=lines)], parser="doc.v1")
