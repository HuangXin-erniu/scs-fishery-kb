from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from .chunking import chunk_document
from .config import DEFAULT_CONFIG, REPO_ROOT
from .models import Chunk, Document
from .parsers import Page as ParsedPage
from .registry import load_registry
from .store import load_chunks

DEFAULT_TERMS = REPO_ROOT / "configs" / "terms.yaml"
TERM_ID = re.compile(r"TERM-\d{3}")
STATUSES = frozenset({"draft", "approved", "stale"})
SOURCE_KINDS = frozenset({"corpus", "glossary", "lexicon"})
REQUIRED = ("id", "standard", "variants", "source", "status")


class TermError(RuntimeError):
    """Raised when a terminology file is malformed."""


def validate_term(term: dict[str, Any]) -> list[str]:
    if not isinstance(term, dict):
        return ["term is not a mapping"]
    term_id = str(term.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in term:
            errors.append(f"{term_id}: missing {key}")
    if not TERM_ID.fullmatch(term_id):
        errors.append(f"{term_id}: id must match TERM-NNN")
    if not str(term.get("standard") or "").strip():
        errors.append(f"{term_id}: standard is empty")
    variants = term.get("variants")
    if not isinstance(variants, list) or not variants:
        errors.append(f"{term_id}: variants must be a non-empty list")
    elif any(not str(item).strip() for item in variants):
        errors.append(f"{term_id}: variants contain an empty value")
    source = term.get("source")
    if not isinstance(source, dict):
        errors.append(f"{term_id}: source is not a mapping")
    else:
        if source.get("kind") not in SOURCE_KINDS:
            errors.append(f"{term_id}: source.kind {source.get('kind')!r} is invalid")
        if not (source.get("doc") or source.get("note")):
            errors.append(f"{term_id}: source needs a doc or a note")
    if term.get("status") not in STATUSES:
        errors.append(f"{term_id}: status {term.get('status')!r} is invalid")
    return errors


def load_terms(path: Path | str = DEFAULT_TERMS) -> list[dict[str, Any]]:
    term_path = Path(path)
    if not term_path.is_file():
        raise TermError(f"term file not found: {term_path}")
    data = yaml.safe_load(term_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise TermError(f"unsupported term schema: {term_path}")
    items = data.get("terms")
    if not isinstance(items, list):
        raise TermError(f"terms is not a list: {term_path}")
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_standard: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{term_path}: entry is not a mapping")
            continue
        term_id = str(item.get("id") or "<unknown>")
        errors.extend(validate_term(item))
        if term_id in seen_ids:
            errors.append(f"{term_id}: duplicate id")
        seen_ids.add(term_id)
        standard = str(item.get("standard") or "")
        if standard in seen_standard:
            errors.append(f"{term_id}: duplicate standard {standard!r}")
        seen_standard.add(standard)
    if errors:
        raise TermError("; ".join(errors))
    return items


def check_terms(
    path: Path | str = DEFAULT_TERMS,
    *,
    data_root: Path | str,
    registry_path: Path | str = DEFAULT_CONFIG,
) -> dict[str, Any]:
    terms = load_terms(path)
    registry = load_registry(registry_path)
    chunks, _manifest = load_chunks(Path(data_root))
    text = " ".join(chunk.text for chunk in chunks)
    errors: list[str] = []
    approved = 0
    for term in terms:
        term_id = str(term["id"])
        source = term.get("source") or {}
        if source.get("kind") == "corpus":
            doc_id = str(source.get("doc") or "")
            if doc_id not in registry:
                errors.append(f"{term_id}: source doc {doc_id!r} is not in the registry")
            section = str(source.get("section") or "")
            if not any(
                chunk.doc_id == doc_id and (not section or chunk.section.startswith(section))
                for chunk in chunks
            ):
                errors.append(f"{term_id}: source section {doc_id} {section} is not indexed")
        if term.get("status") == "approved":
            approved += 1
            if str(term["standard"]) not in text:
                errors.append(f"{term_id}: standard term {term['standard']!r} is not in the corpus")
    return {"terms": len(terms), "approved": approved, "errors": errors}


def term_text(term: dict[str, Any]) -> str:
    source = term.get("source") or {}
    parts = [
        f"规范说法：{term['standard']}",
        "口语/变体：" + "、".join(str(item) for item in term.get("variants") or []),
    ]
    if term.get("region"):
        parts.append("适用地区：" + "、".join(str(item) for item in term["region"]))
    parts.append(f"依据：{source.get('doc') or source.get('note')}")
    return "\n".join(parts)


def term_documents(
    path: Path | str = DEFAULT_TERMS,
    *,
    max_fallback_chars: int = 800,
) -> tuple[list[Document], list[Chunk], list[dict[str, Any]], dict[str, int]]:
    terms = load_terms(path)
    documents: list[Document] = []
    chunks: list[Chunk] = []
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for term in terms:
        if term.get("status") != "approved":
            continue
        text = term_text(term)
        document = Document(
            doc_id=str(term["id"]),
            source_id=str(term["id"]),
            title=str(term["standard"]),
            title_zh=str(term["standard"]),
            publisher="terminology map",
            year=None,
            doc_type="term",
            sensitivity="public",
            language="zh",
            page_count=1,
            file_hash="",
        )
        page = ParsedPage(number=0, lines=text.splitlines())
        made = [
            replace(chunk, kind="term", source_class="reference", trust="standard", review_due="")
            for chunk in chunk_document(document, [page], max_fallback_chars)
        ]
        if not made:
            continue
        documents.append(document)
        chunks.extend(made)
        counts[document.doc_id] = len(made)
        entries.append(
            {
                "id": document.doc_id,
                "hash": "",
                "location": "terms.yaml",
                "format": "term",
                "pages": 1,
                "chunks": len(made),
                "kind": "term",
            }
        )
    return documents, chunks, entries, counts


__all__ = [
    "DEFAULT_TERMS",
    "TermError",
    "check_terms",
    "load_terms",
    "term_documents",
    "validate_term",
]
