from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .chunking import chunk_document
from .corpus import acquired_sources, load_corpus, resolve_source_file
from .models import Document
from .parsers import ParseError, parse_source
from .store import chunk_records, processed_dir, write_json, write_jsonl


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
    chunking = data.get("chunking")
    if not isinstance(chunking, dict) or not isinstance(chunking.get("max_fallback_chars"), int):
        raise IngestError("pipeline.invalid: chunking.max_fallback_chars must be an integer")
    return data


def ingest(config_path: Path, pipeline_path: Path, data_root: Any) -> dict[str, Any]:
    """Parse the configured sources, chunk them and write the processed store."""
    register = load_corpus(config_path)
    pipeline = load_pipeline(Path(pipeline_path))
    sources = {source.id: source for source in acquired_sources(register)}
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
        "sources": source_entries,
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
