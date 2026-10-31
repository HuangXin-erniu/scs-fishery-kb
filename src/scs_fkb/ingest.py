from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .chunking import chunk_document
from .corpus import acquired_sources, load_corpus, read_document_text, resolve_source_file
from .extract import extract_main_text
from .models import Document
from .store import chunk_records, processed_dir, write_json, write_jsonl


def ingest(config_path: Path, data_root: Path) -> dict:
    register = load_corpus(config_path)
    sources = acquired_sources(register)
    root = data_root.expanduser().resolve()

    documents: list[Document] = []
    all_chunks = []
    source_entries = []
    counts: dict[str, int] = {}

    for source in sources:
        path, digest = resolve_source_file(source, root)
        html = read_document_text(path)
        text = extract_main_text(html)
        if not text.strip():
            raise ValueError(f"no body text extracted from {source.id}")
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
            page_count=1,
            file_hash=digest,
        )
        chunks = chunk_document(document, text)
        if not chunks:
            raise ValueError(f"no chunks produced for {source.id}")
        documents.append(document)
        all_chunks.extend(chunks)
        counts[source.id] = len(chunks)
        source_entries.append(
            {
                "id": source.id,
                "hash": digest,
                "location": source.location,
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
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "index_version": index_version,
        "parser": "scs_fkb.extract.v1",
        "chunker": "scs_fkb.chunking.v1",
        "documents": [asdict(document) for document in documents],
        "chunks": len(all_chunks),
        "counts": counts,
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
        "counts": counts,
        "index_version": index_version,
    }
