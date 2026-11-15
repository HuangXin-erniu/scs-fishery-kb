from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..models import Document
from ..registry import load_registry
from ..store import StoreError, read_json, read_jsonl, write_json, write_jsonl
from .chunking import Hierarchy, hierarchical_chunks
from .loaders import LoaderError, load_document, loader_plan
from .snapshot import MANIFEST_NAME, snapshot_registry

PROCESSED = Path("v2") / "processed"
MANIFEST = PROCESSED / "manifest.json"
DOCUMENTS = PROCESSED / "documents.jsonl"
PARENTS = PROCESSED / "parents.jsonl"
CHUNKS = PROCESSED / "chunks.jsonl"


class IngestV2Error(RuntimeError):
    """Raised when the v2 pipeline configuration or a required input is invalid."""


@dataclass(frozen=True)
class BuildResult:
    documents: int
    parents: int
    chunks: int
    pages: int
    counts: dict[str, int]
    parsers: dict[str, str]
    rebuilt: list[str]
    skipped: list[str]
    quarantined: list[dict[str, str]]
    removed: list[str]
    snapshot_manifest_sha256: str
    build_id: str
    manifest_path: str
    data_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def children(self) -> int:
        """Child chunks; ``chunks`` is kept for the manifest field name."""
        return self.chunks


def load_pipeline_v2(path: Path | str) -> dict[str, Any]:
    pipeline_path = Path(path)
    if not pipeline_path.is_file():
        raise IngestV2Error(f"pipeline.missing: {pipeline_path}")
    data = yaml.safe_load(pipeline_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise IngestV2Error(f"pipeline.invalid: {pipeline_path}")
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise IngestV2Error("pipeline.invalid: documents must be a non-empty list")
    if len(set(documents)) != len(documents):
        raise IngestV2Error("pipeline.invalid: duplicate document id")
    chunking = data.get("chunking")
    if not isinstance(chunking, dict) or not isinstance(chunking.get("max_fallback_chars"), int):
        raise IngestV2Error("pipeline.invalid: chunking.max_fallback_chars must be an integer")
    return data


def _source_meta(source: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, str]:
    provenance = source.get("provenance") or {}
    currency = source.get("currency") or {}
    effective = source.get("effective") or {}
    retrieval = source.get("retrieval") or {}
    channel = str(retrieval.get("channel") or "main")
    kind = "corpus" if channel == "main" else channel
    snapshot_hash = str(snapshot.get("sha256") or snapshot.get("tree_sha256") or "")
    return {
        "version_id": f"{source['id']}-{str(source.get('hash') or '')[:12]}",
        "snapshot_hash": snapshot_hash,
        "authority_tier": str(source.get("authority_tier") or ""),
        "ingest_tier": str((source.get("ingest") or {}).get("tier") or "canonical"),
        "level": str(source.get("level") or ""),
        "source_class": str(source.get("source_class") or ""),
        "license": str(source.get("license") or ""),
        "jurisdiction": str(source.get("jurisdiction") or ""),
        "effective_from": str(effective.get("from") or ""),
        "effective_to": str(effective.get("to") or ""),
        "url": str(provenance.get("url") or ""),
        "retrieved_at": str(provenance.get("retrieved_at") or ""),
        "review_due": str(currency.get("review_due") or ""),
        "kind": kind,
    }


def _source_fingerprint(
    source: dict[str, Any], snapshot: dict[str, Any], pipeline: dict[str, Any]
) -> str:
    retrieval = source.get("retrieval") or {}
    payload = {
        "id": source.get("id"),
        "hash": source.get("hash"),
        "format": source.get("format"),
        "location": source.get("location"),
        "authority_tier": source.get("authority_tier"),
        "ingest_tier": (source.get("ingest") or {}).get("tier") or "canonical",
        "level": source.get("level"),
        "source_class": source.get("source_class"),
        "license": source.get("license"),
        "jurisdiction": source.get("jurisdiction"),
        "review_due": (source.get("currency") or {}).get("review_due"),
        "channel": retrieval.get("channel"),
        "snapshot": snapshot.get("sha256") or snapshot.get("tree_sha256"),
        "loader_plan": loader_plan(
            str(source.get("format") or ""), str(retrieval.get("channel") or "corpus")
        ),
        "max_fallback_chars": pipeline["chunking"]["max_fallback_chars"],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _document(source: dict[str, Any], snapshot: dict[str, Any], page_count: int) -> Document:
    meta = _source_meta(source, snapshot)
    year = source.get("year")
    return Document(
        doc_id=str(source["id"]),
        source_id=str(source["id"]),
        title=str(source.get("title") or ""),
        title_zh=str(source.get("title_zh") or source.get("title") or ""),
        publisher=str(source.get("publisher") or ""),
        year=year if isinstance(year, int) else None,
        doc_type=str(source.get("type") or ""),
        sensitivity=str(source.get("sensitivity") or "public"),
        language="zh",
        page_count=page_count,
        file_hash=str(source.get("hash") or ""),
        version_id=meta["version_id"],
        snapshot_hash=meta["snapshot_hash"],
        authority_tier=meta["authority_tier"],
        ingest_tier=meta["ingest_tier"],
        level=meta["level"],
        source_class=meta["source_class"],
        license=meta["license"],
        jurisdiction=meta["jurisdiction"],
        effective_from=meta["effective_from"],
        effective_to=meta["effective_to"],
        url=meta["url"],
        retrieved_at=meta["retrieved_at"],
    )


def _snapshot_file(root: Path, snapshot: dict[str, Any]) -> Path:
    path = root / str(snapshot["snapshot_path"])
    if path.is_dir():
        files = sorted(item for item in path.rglob("*") if item.is_file())
        if len(files) != 1:
            raise LoaderError(
                f"loader.directory: expected one file in {path.name}, found {len(files)}"
            )
        return files[0]
    if not path.is_file():
        raise LoaderError(f"loader.missing: {snapshot['snapshot_path']}")
    return path


def _chunk_digest(children: list[Any]) -> str:
    payload = json.dumps(
        [asdict(child) for child in children], ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        return read_jsonl(path)
    except StoreError:
        return []


def _previous(root: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    manifest: dict[str, Any] = {}
    try:
        manifest = read_json(root / MANIFEST)
    except StoreError:
        pass
    rows = {
        "documents": _read_rows(root / DOCUMENTS),
        "parents": _read_rows(root / PARENTS),
        "chunks": _read_rows(root / CHUNKS),
    }
    return manifest, rows


def _source_rows(
    root: Path,
    source: dict[str, Any],
    snapshot: dict[str, Any],
    pipeline: dict[str, Any],
) -> tuple[Document, Hierarchy, str, str]:
    path = _snapshot_file(root, snapshot)
    retrieval = source.get("retrieval") or {}
    kind = "corpus" if retrieval.get("channel") == "main" else str(retrieval.get("channel"))
    meta = _source_meta(source, snapshot)
    loaded = load_document(path, str(source.get("format") or ""), source_kind=kind)
    document = _document(source, snapshot, len(loaded.parsed.pages))
    hierarchy = hierarchical_chunks(
        document,
        loaded.parsed.pages,
        int(pipeline["chunking"]["max_fallback_chars"]),
        kind=meta["kind"],
        review_due=meta["review_due"],
    )
    return document, hierarchy, loaded.parser, _chunk_digest(hierarchy.children)


def build_v2(
    config_path: Path | str,
    pipeline_path: Path | str,
    data_root: Path | str,
    *,
    refresh_snapshots: bool = True,
) -> BuildResult:
    """Build the v2 store without touching the v1 processed store or index."""
    root = Path(data_root).expanduser().resolve()
    pipeline = load_pipeline_v2(pipeline_path)
    registry = load_registry(config_path)
    if refresh_snapshots:
        snapshots = snapshot_registry(registry, root)
    else:
        snapshots = read_json(root / MANIFEST_NAME)
    source_snapshots = snapshots.get("sources") or {}
    previous_manifest, previous = _previous(root)
    previous_docs = {str(row.get("doc_id")): row for row in previous["documents"]}
    previous_parents: dict[str, list[dict[str, Any]]] = {}
    for row in previous["parents"]:
        previous_parents.setdefault(str(row.get("doc_id")), []).append(row)
    previous_chunks: dict[str, list[dict[str, Any]]] = {}
    for row in previous["chunks"]:
        previous_chunks.setdefault(str(row.get("doc_id")), []).append(row)
    previous_meta = previous_manifest.get("per_document") or {}

    documents: list[dict[str, Any]] = []
    parents: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    rebuilt: list[str] = []
    skipped: list[str] = []
    quarantined: list[dict[str, str]] = []
    parsers: dict[str, str] = {}
    counts: dict[str, int] = {}
    per_document: dict[str, dict[str, Any]] = {}
    pages = 0

    for doc_id in pipeline["documents"]:
        source = registry.get(doc_id)
        if source is None:
            quarantined.append({"doc_id": doc_id, "reason": "source.not_registered"})
            continue
        snapshot = source_snapshots.get(doc_id)
        if not snapshot:
            quarantined.append({"doc_id": doc_id, "reason": "snapshot.missing"})
            continue
        fingerprint = _source_fingerprint(source, snapshot, pipeline)
        cached = previous_meta.get(doc_id) or {}
        if (
            cached.get("source_fingerprint") == fingerprint
            and doc_id in previous_docs
            and doc_id in previous_parents
            and doc_id in previous_chunks
        ):
            documents.append(previous_docs[doc_id])
            parents.extend(previous_parents[doc_id])
            chunks.extend(previous_chunks[doc_id])
            parsers[doc_id] = str(cached.get("parser") or "")
            counts[doc_id] = int(cached.get("children") or len(previous_chunks[doc_id]))
            pages += int(cached.get("pages") or 0)
            per_document[doc_id] = {
                **cached,
                "status": "skipped",
            }
            skipped.append(doc_id)
            continue

        try:
            document, hierarchy, parser, digest = _source_rows(root, source, snapshot, pipeline)
        except (LoaderError, OSError, ValueError) as exc:
            quarantined.append({"doc_id": doc_id, "reason": str(exc)})
            continue

        doc_row = asdict(document)
        parent_rows = [asdict(item) for item in hierarchy.parents]
        child_rows = [asdict(item) for item in hierarchy.children]
        documents.append(doc_row)
        parents.extend(parent_rows)
        chunks.extend(child_rows)
        parsers[doc_id] = parser
        counts[doc_id] = len(child_rows)
        pages += document.page_count
        per_document[doc_id] = {
            "source_hash": source.get("hash"),
            "snapshot_hash": snapshot.get("sha256") or snapshot.get("tree_sha256"),
            "source_fingerprint": fingerprint,
            "parser": parser,
            "pages": document.page_count,
            "parents": len(parent_rows),
            "children": len(child_rows),
            "chunk_digest": digest,
            "status": "rebuilt",
        }
        rebuilt.append(doc_id)

    pipeline_docs = set(pipeline["documents"])
    removed = sorted(doc_id for doc_id in previous_docs if doc_id not in pipeline_docs)
    documents.sort(key=lambda row: str(row.get("doc_id")))
    parents.sort(key=lambda row: str(row.get("chunk_id")))
    chunks.sort(key=lambda row: str(row.get("chunk_id")))

    content_index = {
        doc_id: {
            "chunk_digest": meta.get("chunk_digest"),
            "snapshot_hash": meta.get("snapshot_hash"),
            "parser": meta.get("parser"),
        }
        for doc_id, meta in per_document.items()
    }
    build_id = hashlib.sha256(
        json.dumps(
            {
                "snapshot_manifest": snapshots.get("snapshot_manifest_sha256"),
                "content_index": content_index,
                "documents": len(documents),
                "chunks": len(chunks),
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    source_manifest_hash = hashlib.sha256(
        json.dumps(
            [
                {
                    "id": source["id"],
                    "hash": source.get("hash"),
                    "format": source.get("format"),
                    "location": source.get("location"),
                }
                for source in (
                    registry[doc_id] for doc_id in pipeline["documents"] if doc_id in registry
                )
            ],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 2,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "build_id": build_id,
        "snapshot_manifest_sha256": snapshots.get("snapshot_manifest_sha256"),
        "source_manifest_hash": source_manifest_hash,
        "documents": len(documents),
        "parents": len(parents),
        "chunks": len(chunks),
        "pages": pages,
        "counts": counts,
        "parsers": parsers,
        "per_document": per_document,
        "rebuilt": rebuilt,
        "skipped": skipped,
        "quarantined": quarantined,
        "removed": removed,
    }
    write_jsonl(root / DOCUMENTS, documents)
    write_jsonl(root / PARENTS, parents)
    write_jsonl(root / CHUNKS, chunks)
    write_json(root / MANIFEST, manifest)

    return BuildResult(
        documents=len(documents),
        parents=len(parents),
        chunks=len(chunks),
        pages=pages,
        counts=counts,
        parsers=parsers,
        rebuilt=rebuilt,
        skipped=skipped,
        quarantined=quarantined,
        removed=removed,
        snapshot_manifest_sha256=str(snapshots.get("snapshot_manifest_sha256") or ""),
        build_id=build_id,
        manifest_path=str(root / MANIFEST),
        data_root=str(root),
    )


__all__ = [
    "BuildResult",
    "IngestV2Error",
    "build_v2",
    "load_pipeline_v2",
]
