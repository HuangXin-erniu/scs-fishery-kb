from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import REPO_ROOT
from ..models import Chunk
from ..store import read_json, write_json

INDEX_ROOT = Path("v2") / "index"
VERSIONS = INDEX_ROOT / "versions"
MANIFEST = INDEX_ROOT / "manifest.json"
CURRENT = INDEX_ROOT / "current.json"
LEGACY_INDEX = INDEX_ROOT / "lancedb"
TABLE_NAME = "chunks"
BM25 = {"tokenizer": "char-bigram", "k1": 1.5, "b": 0.75}


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
    version_path: str = ""

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
        "ingest_tier": chunk.ingest_tier,
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


def _store_at(table_dir: Path, *, mode: str) -> Any:
    from llama_index.vector_stores.lancedb import LanceDBVectorStore

    table_dir.parent.mkdir(parents=True, exist_ok=True)
    return LanceDBVectorStore(uri=str(table_dir), table_name=TABLE_NAME, mode=mode)


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


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _version_dir(root: Path, index_version: str) -> Path:
    return root / VERSIONS / index_version


def _manifest_for(
    *,
    index_version: str,
    model: str,
    dim: int,
    chunks: int,
    documents: int,
    table_rows: int,
    chunk_hash: str,
    per_document: dict[str, str],
    source_hash: str,
    rebuilt: list[str],
    removed: list[str],
    build_seconds: float,
    peak_rss_mb: float,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "index_version": index_version,
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_commit": _git_commit(),
        "model": model,
        "dim": dim,
        "embedding": {"model": model, "dim": dim, "normalize": True},
        "bm25": dict(BM25),
        "reranker": None,
        "chunks": chunks,
        "documents": documents,
        "table_rows": table_rows,
        "chunk_digest": chunk_hash,
        "per_document": per_document,
        "snapshot_manifest_sha256": source_hash,
        "pipeline_config_sha256": _file_sha256(REPO_ROOT / "configs" / "pipeline.yaml"),
        "build_seconds": round(build_seconds, 2),
        "peak_rss_mb": round(peak_rss_mb, 1),
        "rebuilt": rebuilt,
        "removed": removed,
    }


def _write_current(root: Path, index_version: str) -> None:
    path = root / CURRENT
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "index_version": index_version,
        "table": str(Path("versions") / index_version / "lancedb"),
        "manifest": str(Path("versions") / index_version / "manifest.json"),
        "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def current_version(data_root: Path | str) -> dict[str, Any] | None:
    root = Path(data_root).expanduser().resolve()
    path = root / CURRENT
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def build_index_v2(
    data_root: Path | str,
    encoder: Any,
    *,
    force: bool = False,
) -> IndexBuildResult:
    """Build an immutable version and switch the current pointer atomically."""
    root = Path(data_root).expanduser().resolve()
    chunks = load_chunks_v2(root)
    digest = chunk_digest(chunks)
    per_doc = per_document_digests(chunks)
    model = str(encoder.model_id)
    dim = int(encoder.dim)
    source_hash = _source_manifest_hash(root)
    fingerprint = f"{model}|{dim}|{digest}|{source_hash}".encode()
    index_version = hashlib.sha256(fingerprint).hexdigest()[:12]
    version_dir = _version_dir(root, index_version)
    table_dir = version_dir / "lancedb"
    started = time.perf_counter()
    current = current_version(root)
    if (
        not force
        and current is not None
        and current.get("index_version") == index_version
        and table_dir.is_dir()
    ):
        manifest = read_json(version_dir / "manifest.json")
        return IndexBuildResult(
            index_version=index_version,
            model=model,
            dim=dim,
            chunks=len(chunks),
            documents=len(per_doc),
            table_rows=int(manifest.get("table_rows") or 0),
            build_seconds=round(time.perf_counter() - started, 2),
            peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1),
            no_op=True,
            rebuilt=[],
            removed=[],
            manifest_path=str(version_dir / "manifest.json"),
            version_path=str(version_dir),
        )

    previous = {}
    try:
        previous = read_json(root / MANIFEST)
    except Exception:  # noqa: BLE001 - first build
        previous = {}
    removed = sorted(set(previous.get("per_document") or {}) - set(per_doc))

    if version_dir.exists():
        shutil.rmtree(version_dir)
    store = _store_at(table_dir, mode="overwrite")
    vectors = encoder.embed_passages([chunk.text for chunk in chunks])
    store.add([_node(chunk, vector) for chunk, vector in zip(chunks, vectors, strict=True)])
    rows = _table_rows(store)
    manifest = _manifest_for(
        index_version=index_version,
        model=model,
        dim=dim,
        chunks=len(chunks),
        documents=len(per_doc),
        table_rows=rows,
        chunk_hash=digest,
        per_document=per_doc,
        source_hash=source_hash,
        rebuilt=sorted(per_doc),
        removed=removed,
        build_seconds=time.perf_counter() - started,
        peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024,
    )
    write_json(version_dir / "manifest.json", manifest)
    write_json(root / MANIFEST, manifest)
    _write_current(root, index_version)
    prune_versions(root, keep=2)
    return IndexBuildResult(
        index_version=index_version,
        model=model,
        dim=dim,
        chunks=len(chunks),
        documents=len(per_doc),
        table_rows=rows,
        build_seconds=float(manifest["build_seconds"]),
        peak_rss_mb=float(manifest["peak_rss_mb"]),
        no_op=False,
        rebuilt=sorted(per_doc),
        removed=removed,
        manifest_path=str(version_dir / "manifest.json"),
        version_path=str(version_dir),
    )


def open_index(data_root: Path | str, encoder: Any) -> Any:
    from llama_index.core import VectorStoreIndex

    from .embedding import EncoderEmbedding

    root = Path(data_root).expanduser().resolve()
    current = current_version(root)
    table_dir = root / LEGACY_INDEX
    if current is not None:
        candidate = root / VERSIONS / str(current.get("index_version") or "") / "lancedb"
        if candidate.is_dir():
            table_dir = candidate
    store = _store_at(table_dir, mode="append")
    if not _table_exists(store):
        raise IndexError_("dense index table is missing; run scripts/build_index_v2.py")
    return VectorStoreIndex.from_vector_store(store, embed_model=EncoderEmbedding(encoder))


def list_versions(data_root: Path | str) -> list[dict[str, Any]]:
    root = Path(data_root).expanduser().resolve()
    rows: list[dict[str, Any]] = []
    directory = root / VERSIONS
    if not directory.is_dir():
        return rows
    for path in directory.iterdir():
        if not path.is_dir():
            continue
        try:
            manifest = read_json(path / "manifest.json")
        except Exception:  # noqa: BLE001 - incomplete version
            continue
        rows.append(
            {
                "index_version": str(manifest.get("index_version") or path.name),
                "built_at": str(manifest.get("built_at") or ""),
                "documents": int(manifest.get("documents") or 0),
                "chunks": int(manifest.get("chunks") or 0),
                "path": str(path),
            }
        )
    rows.sort(key=lambda row: row["built_at"], reverse=True)
    return rows


def rollback_index(data_root: Path | str) -> dict[str, Any]:
    root = Path(data_root).expanduser().resolve()
    versions = list_versions(root)
    current = current_version(root)
    if len(versions) < 2 or current is None:
        raise IndexError_("no previous index version to roll back to")
    current_id = str(current.get("index_version") or "")
    previous = next((row for row in versions if row["index_version"] != current_id), None)
    if previous is None or not (root / VERSIONS / previous["index_version"] / "lancedb").is_dir():
        raise IndexError_("previous index version is incomplete")
    _write_current(root, previous["index_version"])
    return {
        "rolled_back_from": current_id,
        "rolled_back_to": previous["index_version"],
        "built_at": previous["built_at"],
    }


def prune_versions(data_root: Path | str, *, keep: int = 2) -> list[str]:
    root = Path(data_root).expanduser().resolve()
    if keep < 1:
        raise IndexError_("keep must be at least 1")
    versions = list_versions(root)
    current = current_version(root)
    current_id = str((current or {}).get("index_version") or "")
    removed: list[str] = []
    retained = 0
    for row in versions:
        if row["index_version"] == current_id:
            retained += 1
            continue
        if retained < keep:
            retained += 1
            continue
        path = root / VERSIONS / row["index_version"]
        shutil.rmtree(path, ignore_errors=True)
        removed.append(row["index_version"])
    return removed


def dense_search(index: Any, query: str, top_k: int = 30) -> list[tuple[str, float]]:
    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(query)
    return [(str(node.node.node_id), float(node.score or 0.0)) for node in nodes]


__all__ = [
    "IndexBuildResult",
    "IndexError_",
    "build_index_v2",
    "chunk_digest",
    "current_version",
    "dense_search",
    "list_versions",
    "load_chunks_v2",
    "open_index",
    "per_document_digests",
    "prune_versions",
    "rollback_index",
]
