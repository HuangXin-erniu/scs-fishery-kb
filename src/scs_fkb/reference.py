from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import yaml

from .bm25 import BM25Index
from .chunking import chunk_document
from .config import REPO_ROOT
from .config import data_root as default_data_root
from .expand import DEFAULT_BRIDGE, concepts_for, load_bridge
from .models import Document, SearchHit
from .parsers.html import parse

DEFAULT_CATALOG = REPO_ROOT / "configs" / "cwp-handbook.yaml"

SLUG_BY_FILE = {
    "cwp-catch-and-landings.html": "catch",
    "cwp-fishing-effort.html": "effort",
    "cwp-fishing-gear-classification.html": "gear",
}


NOMINAL_CONCEPTS = {"catch", "landings", "effort"}


class ReferenceError(RuntimeError):
    """Raised when a reference file is missing or does not match its catalog hash."""


@lru_cache(maxsize=4)
def _index(catalog_path: str, root: str) -> BM25Index:
    catalog_file = Path(catalog_path)
    if not catalog_file.is_file():
        raise ReferenceError(f"reference catalog not found: {catalog_file}")
    catalog = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
    series = str(catalog.get("series") or "")
    if not series or not isinstance(catalog.get("pages"), list):
        raise ReferenceError(f"reference catalog is incomplete: {catalog_file}")

    chunks = []
    for page in catalog["pages"]:
        file_name = str(page["file"])
        path = Path(root) / "raw" / series / file_name
        if not path.is_file():
            raise ReferenceError(f"reference file not found: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(page.get("sha256")):
            raise ReferenceError(f"reference hash mismatch: {file_name}")
        parsed = parse(path)
        doc_id = f"{series}-{SLUG_BY_FILE.get(file_name, path.stem)}"
        document = Document(
            doc_id=doc_id,
            source_id=series,
            title=str(page.get("title") or file_name),
            title_zh=str(page.get("title") or file_name),
            publisher=str(catalog.get("publisher") or ""),
            year=None,
            doc_type="standard",
            sensitivity="public",
            language="en",
            page_count=len(parsed.pages),
            file_hash=digest,
        )
        chunks.extend(chunk_document(document, parsed.pages))
    return BM25Index(chunks)


def lookup(
    question: str,
    top_k: int = 3,
    root: Path | str | None = None,
    catalog_path: Path | str = DEFAULT_CATALOG,
    bridge_path: Path | str = DEFAULT_BRIDGE,
) -> list[SearchHit]:
    """Return CWP passages for the English concepts found in the question."""
    concepts = concepts_for(question, load_bridge(Path(bridge_path)))
    if not concepts:
        return []
    if NOMINAL_CONCEPTS & set(concepts):
        concepts = concepts + ["nominal"]
    base = Path(root) if root else default_data_root()
    index = _index(str(catalog_path), str(base.expanduser().resolve()))
    return index.search(" ".join(concepts), top_k=top_k)


def lookup_term(term: str, top_k: int = 3, **kwargs) -> list[SearchHit]:
    """Alias of lookup for a single term."""
    return lookup(term, top_k=top_k, **kwargs)
