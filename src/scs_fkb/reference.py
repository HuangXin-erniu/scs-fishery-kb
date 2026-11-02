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
from .parsers import parse_source
from .parsers.html import parse

DEFAULT_CATALOG = REPO_ROOT / "configs" / "cwp-handbook.yaml"
DEFAULT_COLLECTIONS = REPO_ROOT / "configs" / "reference-collections.yaml"

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


def load_collections(path: Path | str = DEFAULT_COLLECTIONS) -> dict[str, dict[str, object]]:
    """Load the named reference collections and validate their shape."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ReferenceError(f"reference collections not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    collections = data.get("collections") if isinstance(data, dict) else None
    if not isinstance(collections, dict) or not collections:
        raise ReferenceError(f"reference collections are empty: {config_path}")
    for name, collection in collections.items():
        documents = collection.get("documents") if isinstance(collection, dict) else None
        if not isinstance(documents, list) or not documents:
            raise ReferenceError(f"collection has no documents: {name}")
        for document in documents:
            if not document.get("id") or not document.get("file") or not document.get("sha256"):
                raise ReferenceError(f"collection document is incomplete: {name}")
    return collections


@lru_cache(maxsize=8)
def _collection_index(config_path: str, name: str, root: str) -> BM25Index:
    collections = load_collections(config_path)
    collection = collections[name]
    chunks = []
    for entry in collection["documents"]:  # type: ignore[index]
        path = Path(root) / str(entry["file"])
        if not path.is_file():
            raise ReferenceError(f"reference file not found: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(entry["sha256"]):
            raise ReferenceError(f"reference hash mismatch: {entry['id']}")
        parsed = parse_source(path, "pdf" if path.suffix.lower() == ".pdf" else "html")
        document = Document(
            doc_id=str(entry["id"]),
            source_id=str(entry["id"]),
            title=str(entry.get("title") or entry["id"]),
            title_zh=str(entry.get("title") or entry["id"]),
            publisher="",
            year=None,
            doc_type="standard",
            sensitivity="public",
            language=str(entry.get("language") or "en"),
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
    collection: str = "cwp",
    collections_path: Path | str = DEFAULT_COLLECTIONS,
) -> list[SearchHit]:
    """Return passages from the named reference collection."""
    base = Path(root) if root else default_data_root()
    resolved = str(base.expanduser().resolve())
    if collection == "cwp":
        concepts = concepts_for(question, load_bridge(Path(bridge_path)))
        if not concepts:
            return []
        if NOMINAL_CONCEPTS & set(concepts):
            concepts = concepts + ["nominal"]
        index = _index(str(catalog_path), resolved)
        return index.search(" ".join(concepts), top_k=top_k)
    if collection not in {"product", "policy"}:
        raise ReferenceError(f"unknown reference collection: {collection}")
    config = load_collections(collections_path)[collection]
    if collection == "product":
        allowed = {str(concept).lower() for concept in config.get("concepts") or []}
        concepts = concepts_for(question, load_bridge(Path(bridge_path)))
        matched = [concept for concept in concepts if concept.lower() in allowed]
        if not matched:
            return []
        # Search with the bridged English concepts plus the original question so that a
        # Chinese-language document in the same collection stays reachable, while English
        # documents keep ranking on the concept terms.
        query = " ".join([*matched, question])
    else:
        cues = [str(cue) for cue in config.get("cues") or []]
        if cues and not any(cue in question for cue in cues):
            return []
        query = question
    index = _collection_index(str(collections_path), collection, resolved)
    return index.search(query, top_k=top_k)


def lookup_term(term: str, top_k: int = 3, **kwargs) -> list[SearchHit]:
    """Alias of lookup for a single term."""
    return lookup(term, top_k=top_k, **kwargs)
