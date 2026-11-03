from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .chunking import chunk_document
from .corpus import acquired_sources, load_corpus, resolve_source_file
from .knowledge import load_knowledge, stale_reasons
from .models import Chunk, Document
from .parsers import Page as ParsedPage
from .parsers import ParseError, parse_source
from .store import chunk_records, processed_dir, write_json, write_jsonl
from .web import load_cards


class IngestError(RuntimeError):
    """Raised when the pipeline configuration or a document cannot be ingested."""


def load_pipeline(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise IngestError(f"pipeline.missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise IngestError(f"pipeline.invalid: {path} must be a mapping")
    if data.get("schema_version") != 1:
        raise IngestError(f"pipeline.invalid: unsupported schema_version in {path}")
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise IngestError(f"pipeline.invalid: {path} lists no documents")
    if not all(isinstance(item, str) and item for item in documents):
        raise IngestError("pipeline.invalid: document ids must be non-empty strings")
    if len(set(documents)) != len(documents):
        raise IngestError("pipeline.invalid: document ids must be unique")
    chunking = data.get("chunking")
    if not isinstance(chunking, dict) or not isinstance(chunking.get("max_fallback_chars"), int):
        raise IngestError("pipeline.invalid: chunking.max_fallback_chars must be an integer")
    return data


def web_card_documents(
    cards_path: Path,
    data_root: Path,
    max_fallback_chars: int,
) -> tuple[list[Document], list[Chunk], list[dict[str, Any]], dict[str, int]]:
    """Turn cached ok cards into documents and chunks; skip unusable cards."""
    cards_file = Path(cards_path)
    if not cards_file.is_file():
        return [], [], [], {}
    cards = load_cards(cards_file)["cards"]
    cache = Path(data_root) / "web"
    documents: list[Document] = []
    chunks: list[Chunk] = []
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for card in cards:
        if card.get("status") != "ok" or not card.get("file"):
            continue
        text_path = cache / str(card["file"])
        if not text_path.is_file():
            continue
        text = text_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        document = Document(
            doc_id=str(card["id"]),
            source_id=str(card["id"]),
            title=str(card["title"]),
            title_zh=str(card["title"]),
            publisher=str(card["publisher"]),
            year=None,
            doc_type="web_card",
            sensitivity=str(card["sensitivity"]),
            language="zh",
            page_count=1,
            file_hash=str(card["sha256"]),
        )
        page = ParsedPage(number=0, lines=text.splitlines())
        made = [
            replace(
                chunk,
                url=str(card["url"]),
                retrieved_at=str(card["fetched_at"]),
                kind="web",
                source_class="reference",
                trust="standard",
                review_due="",
            )
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
                "hash": document.file_hash,
                "location": f"web/{card['file']}",
                "format": "web",
                "pages": 1,
                "chunks": len(made),
                "kind": "web_card",
            }
        )
    return documents, chunks, entries, counts


def _note_trust(note: dict[str, Any], registry_meta: dict[str, Any]) -> str:
    for source in note.get("sources") or []:
        doc = source.get("doc")
        if doc and str((registry_meta.get(doc) or {}).get("source_class")) in {
            "normative",
            "official_statistics",
        }:
            return "authoritative"
    return "standard"


def knowledge_documents(
    knowledge_dir: Path,
    cards_path: Path,
    max_fallback_chars: int,
    *,
    today: Any = None,
    registry_meta: dict[str, Any] | None = None,
) -> tuple[list[Document], list[Chunk], list[dict[str, Any]], dict[str, int]]:
    """Turn approved, fresh knowledge notes into documents and chunks."""
    directory = Path(knowledge_dir)
    if not directory.is_dir():
        return [], [], [], {}
    card_hashes: dict[str, str] = {}
    if Path(cards_path).is_file():
        for card in load_cards(Path(cards_path))["cards"]:
            card_hashes[str(card["id"])] = str(card.get("sha256") or "")
    current = today or datetime.now(UTC).date()
    meta = registry_meta or {}
    documents: list[Document] = []
    chunks: list[Chunk] = []
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = load_knowledge(path)
        for note in data["notes"]:
            if note["status"] != "approved":
                continue
            reasons = stale_reasons(note, card_hashes, current)
            if reasons:
                continue
            text = "\n".join(
                [str(note["title"]), str(note["summary"])]
                + [f"{fact['label']}：{fact['value']}" for fact in note["facts"]]
            )
            document = Document(
                doc_id=str(note["id"]),
                source_id=str(note["id"]),
                title=str(note["title"]),
                title_zh=str(note["title"]),
                publisher="knowledge note",
                year=None,
                doc_type="knowledge_note",
                sensitivity="public",
                language="zh",
                page_count=1,
                file_hash=str((note["sources"][0] or {}).get("sha256") or ""),
            )
            page = ParsedPage(number=0, lines=text.splitlines())
            first = note["sources"][0]
            made = [
                replace(
                    chunk,
                    url=str(first.get("url") or ""),
                    retrieved_at=str(note["as_of"]),
                    kind="note",
                    source_class="reference",
                    trust=_note_trust(note, meta),
                    review_due=str(note["review_due"]),
                )
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
                    "hash": document.file_hash,
                    "location": f"knowledge/{path.name}",
                    "format": "note",
                    "pages": 1,
                    "chunks": len(made),
                    "kind": "knowledge_note",
                }
            )
    return documents, chunks, entries, counts


def ingest(
    config_path: Path,
    pipeline_path: Path,
    data_root: Any,
    web_cards_path: Path | None = None,
    knowledge_dir: Path | None = None,
    include_web: bool = True,
    include_knowledge: bool = True,
) -> dict[str, Any]:
    """Parse the configured sources, chunk them and write the processed store."""
    register = load_corpus(config_path)
    pipeline = load_pipeline(Path(pipeline_path))
    sources = {source.id: source for source in acquired_sources(register)}
    registry_meta = {
        entry["id"]: entry
        for entry in yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))["sources"]
        if isinstance(entry, dict) and entry.get("id")
    }
    root = Path(data_root).expanduser().resolve()
    max_chars = pipeline["chunking"]["max_fallback_chars"]

    documents: list[Document] = []
    all_chunks = []
    counts: dict[str, int] = {}
    page_counts: dict[str, int] = {}
    parsers: dict[str, str] = {}
    source_entries = []

    for doc_id in pipeline["documents"]:
        source = sources.get(doc_id)
        if source is None:
            raise IngestError(f"source.missing: {doc_id} is not an acquired source")
        if source.sensitivity != "public":
            raise IngestError(
                f"source.sensitivity: {doc_id} is {source.sensitivity}; "
                "the local pipeline indexes public sources only"
            )
        path, digest = resolve_source_file(source, root)
        parsed = parse_source(path, source.format)

        document = Document(
            doc_id=source.id,
            source_id=source.id,
            title=source.title,
            title_zh=source.title_zh,
            publisher=source.publisher,
            year=source.year,
            doc_type=source.doc_type,
            sensitivity=source.sensitivity,
            language="zh",
            page_count=len(parsed.pages),
            file_hash=digest,
        )
        chunks = chunk_document(document, parsed.pages, max_chars)
        meta = registry_meta.get(source.id, {})
        source_class = str(meta.get("source_class") or "")
        trust = (
            "authoritative" if source_class in {"normative", "official_statistics"} else "standard"
        )
        review_due = str((meta.get("currency") or {}).get("review_due") or "")
        chunks = [
            replace(chunk, source_class=source_class, trust=trust, review_due=review_due)
            for chunk in chunks
        ]
        if not chunks:
            raise IngestError(f"text.empty: no chunks produced for {source.id}")

        documents.append(document)
        all_chunks.extend(chunks)
        counts[source.id] = len(chunks)
        page_counts[source.id] = len(parsed.pages)
        parsers[source.id] = parsed.parser
        source_entries.append(
            {
                "id": source.id,
                "hash": digest,
                "location": source.location,
                "format": source.format,
                "pages": len(parsed.pages),
                "chunks": len(chunks),
            }
        )

    cards_file = (
        Path(web_cards_path)
        if web_cards_path is not None
        else Path(pipeline_path).parent / "web-cards.yaml"
    )
    web_documents, web_chunks, web_entries, web_counts = (
        web_card_documents(cards_file, root, max_chars) if include_web else ([], [], [], {})
    )
    documents.extend(web_documents)
    all_chunks.extend(web_chunks)
    counts.update(web_counts)
    for entry in web_entries:
        parsers[entry["id"]] = "web"

    notes_dir = (
        Path(knowledge_dir)
        if knowledge_dir is not None
        else Path(pipeline_path).parent / "knowledge"
    )
    note_documents, note_chunks, note_entries, note_counts = (
        knowledge_documents(notes_dir, cards_file, max_chars, registry_meta=registry_meta)
        if include_knowledge
        else ([], [], [], {})
    )
    documents.extend(note_documents)
    all_chunks.extend(note_chunks)
    counts.update(note_counts)
    for entry in note_entries:
        parsers[entry["id"]] = "note"

    chunk_digest = hashlib.sha256(
        "".join(f"{chunk.chunk_id}\n{chunk.text}\n" for chunk in all_chunks).encode("utf-8")
    ).hexdigest()
    index_version = hashlib.sha256(
        json.dumps(
            {"sources": source_entries, "chunk_digest": chunk_digest},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]

    manifest = {
        "schema_version": 2,
        "created_at": datetime.now(UTC).isoformat(),
        "index_version": index_version,
        "parsers": parsers,
        "documents": [asdict(document) for document in documents],
        "chunks": len(all_chunks),
        "counts": counts,
        "pages": page_counts,
        "sources": source_entries + web_entries + note_entries,
        "chunk_digest": chunk_digest,
    }

    directory = processed_dir(root)
    write_jsonl(directory / "documents.jsonl", [asdict(document) for document in documents])
    write_jsonl(directory / "chunks.jsonl", chunk_records(all_chunks))
    write_json(directory / "manifest.json", manifest)

    return {
        "data_root": str(root),
        "documents": len(documents),
        "chunks": len(all_chunks),
        "pages": page_counts,
        "counts": counts,
        "parsers": parsers,
        "index_version": index_version,
    }


__all__ = ["IngestError", "ParseError", "ingest", "load_pipeline"]
