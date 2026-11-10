from __future__ import annotations

import hashlib
import json
import resource
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..models import Chunk
from ..store import read_json, write_json

INDEX_DIR = Path("v2") / "index" / "lancedb"
MANIFEST = Path("v2") / "index" / "manifest.json"
TABLE_NAME = "chunks"


class IndexError_(RuntimeError):
    """Raised when the dense index cannot be built or opened."""


@dataclass(frozen=True)
class IndexBuildResult:
    index_version: str
    model: str
    dim: int
    chunks: int
    documents: int
    table_rows: int
    build_seconds: float
    peak_rss_mb: float
    no_op: bool
    rebuilt: list[str]
    removed: list[str]
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_chunks_v2(data_root: Path | str) -> list[Chunk]:
    path = Path(data_root).expanduser().resolve() / "v2" / "processed" / "chunks.jsonl"
    if not path.is_file():
        raise IndexError_(f"v2 chunks not found: {path}")
    chunks: list[Chunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(Chunk(**json.loads(line)))
    if not chunks:
        raise IndexError_("v2 chunks are empty")
    return chunks


def _digest(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def chunk_digest(chunks: list[Chunk]) -> str:
    return _digest([asdict(chunk) for chunk in chunks])


def per_document_digests(chunks: list[Chunk]) -> dict[str, str]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk.doc_id, []).append(asdict(chunk))
    return {doc_id: _digest(rows) for doc_id, rows in grouped.items()}


def _node(chunk: Chunk, embedding: list[float]) -> Any:
    from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode

    metadata = {
        "doc_id": chunk.doc_id,
        "source_id": chunk.source_id,
        "page": chunk.page,
        "section": chunk.section,
        "section_path": chunk.section_path,
        "chunk_type": chunk.chunk_type,
        "parent_id": chunk.parent_id,
        "sensitivity": chunk.sensitivity,
        "authority_tier": chunk.authority_tier,
        "level": chunk.level,
        "source_class": chunk.source_class,
        "trust": chunk.trust,
        "jurisdiction": chunk.jurisdiction,
        "license": chunk.license,
        "effective_from": chunk.effective_from,
        "effective_to": chunk.effective_to,
        "review_due": chunk.review_due,
        "url": chunk.url,
        "retrieved_at": chunk.retrieved_at,
        "version_id": chunk.version_id,
        "snapshot_hash": chunk.snapshot_hash,
    }
    node = TextNode(text=chunk.text, id_=chunk.chunk_id, metadata=metadata)
    node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=chunk.doc_id)
    node.embedding = embedding
    return node


def _store(root: Path, *, mode: str) -> Any:
    from llama_index.vector_stores.lancedb import LanceDBVectorStore

    return LanceDBVectorStore(uri=str(root / INDEX_DIR), table_name=TABLE_NAME, mode=mode)


def _table_rows(store: Any) -> int:
    try:
        return int(store.table.count_rows())
    except Exception:  # noqa: BLE001 - optional backend diagnostics
        return 0


def _table_exists(store: Any) -> bool:
    try:
        store.table.count_rows()
        return True
    except Exception:  # noqa: BLE001 - optional backend diagnostics
        return False


def _source_manifest_hash(root: Path) -> str:
    path = root / "v2" / "processed" / "manifest.json"
    try:
        manifest = read_json(path)
    except Exception:  # noqa: BLE001 - optional metadata
        return ""
    return str(manifest.get("snapshot_manifest_sha256") or "")


def build_index_v2(
    data_root: Path | str,
    encoder: Any,
    *,
    force: bool = False,
) -> IndexBuildResult:
    """Build or incrementally update the LanceDB table from v2 child chunks."""
    root = Path(data_root).expanduser().resolve()
    chunks = load_chunks_v2(root)
    digest = chunk_digest(chunks)
    per_doc = per_document_digests(chunks)
    model = str(encoder.model_id)
    dim = int(encoder.dim)
    source_hash = _source_manifest_hash(root)
    index_version = hashlib.sha256(f"{model}|{dim}|{digest}|{source_hash}".encode()).hexdigest()[
        :12
    ]
    manifest_path = root / MANIFEST
    previous: dict[str, Any] = {}
    try:
        previous = read_json(manifest_path)
    except Exception:  # noqa: BLE001 - first build
        previous = {}

    started = time.perf_counter()
    try:
        store = _store(root, mode="append")
        table_ready = _table_exists(store)
    except Exception:  # noqa: BLE001 - no table yet
        store = _store(root, mode="overwrite")
        table_ready = False
    unchanged = (
        previous.get("chunk_digest") == digest
        and previous.get("model") == model
        and previous.get("dim") == dim
        and table_ready
    )
    if unchanged and not force:
        return IndexBuildResult(
            index_version=str(previous.get("index_version") or index_version),
            model=model,
            dim=dim,
            chunks=len(chunks),
            documents=len(per_doc),
            table_rows=_table_rows(store),
            build_seconds=round(time.perf_counter() - started, 2),
            peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1),
            no_op=True,
            rebuilt=[],
            removed=[],
            manifest_path=str(manifest_path),
        )

    full_rebuild = (
        force or not table_ready or previous.get("model") != model or previous.get("dim") != dim
    )
    rebuilt: list[str] = []
    removed: list[str] = []
    if full_rebuild:
        store = _store(root, mode="overwrite")
        vectors = encoder.embed_passages([chunk.text for chunk in chunks])
        nodes = [_node(chunk, vector) for chunk, vector in zip(chunks, vectors, strict=True)]
        store.add(nodes)
        rebuilt = sorted(per_doc)
        previous_docs = previous.get("per_document") or {}
        removed = sorted(set(previous_docs) - set(per_doc))
    else:
        previous_docs = previous.get("per_document") or {}
        changed = sorted(
            doc_id for doc_id, value in per_doc.items() if previous_docs.get(doc_id) != value
        )
        removed = sorted(set(previous_docs) - set(per_doc))
        for doc_id in changed + removed:
            try:
                store.table.delete(f"doc_id = '{doc_id}'")
            except Exception as exc:  # noqa: BLE001 - surface as index failure
                raise IndexError_(f"index.delete_failed: {doc_id}: {exc}") from exc
        changed_chunks = [chunk for chunk in chunks if chunk.doc_id in set(changed)]
        if changed_chunks:
            vectors = encoder.embed_passages([chunk.text for chunk in changed_chunks])
            store.add(
                [
                    _node(chunk, vector)
                    for chunk, vector in zip(changed_chunks, vectors, strict=True)
                ]
            )
        rebuilt = changed

    manifest = {
        "schema_version": 1,
        "index_version": index_version,
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "model": model,
        "dim": dim,
        "chunks": len(chunks),
        "documents": len(per_doc),
        "table_rows": _table_rows(store),
        "chunk_digest": digest,
        "per_document": per_doc,
        "snapshot_manifest_sha256": source_hash,
        "build_seconds": round(time.perf_counter() - started, 2),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1),
        "rebuilt": rebuilt,
        "removed": removed,
    }
    write_json(manifest_path, manifest)
    return IndexBuildResult(
        index_version=index_version,
        model=model,
        dim=dim,
        chunks=len(chunks),
        documents=len(per_doc),
        table_rows=int(manifest["table_rows"]),
        build_seconds=float(manifest["build_seconds"]),
        peak_rss_mb=float(manifest["peak_rss_mb"]),
        no_op=False,
        rebuilt=rebuilt,
        removed=removed,
        manifest_path=str(manifest_path),
    )


def open_index(data_root: Path | str, encoder: Any) -> Any:
    from llama_index.core import VectorStoreIndex

    from .embedding import EncoderEmbedding

    root = Path(data_root).expanduser().resolve()
    store = _store(root, mode="append")
    if not _table_exists(store):
        raise IndexError_("dense index table is missing; run scripts/build_index_v2.py")
    return VectorStoreIndex.from_vector_store(store, embed_model=EncoderEmbedding(encoder))


def dense_search(index: Any, query: str, top_k: int = 30) -> list[tuple[str, float]]:
    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(query)
    return [(str(node.node.node_id), float(node.score or 0.0)) for node in nodes]


__all__ = [
    "IndexBuildResult",
    "IndexError_",
    "build_index_v2",
    "chunk_digest",
    "dense_search",
    "load_chunks_v2",
    "open_index",
    "per_document_digests",
]
