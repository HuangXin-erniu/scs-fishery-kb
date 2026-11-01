from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .bm25 import SENSITIVITY_ORDER
from .embed import Encoder
from .models import Chunk, SearchHit


class DenseError(RuntimeError):
    """Raised when the dense index is missing or malformed."""


def embeddings_dir(root: Path) -> Path:
    return root / "embeddings"


def index_path(root: Path, model_id: str, index_version: str) -> Path:
    safe = model_id.replace("/", "_").replace(":", "_")
    return embeddings_dir(root) / f"{safe}-{index_version}.jsonl"


class DenseIndex:
    def __init__(self, rows: list[dict[str, Any]], model_id: str, index_version: str) -> None:
        self.rows = rows
        self.model_id = model_id
        self.index_version = index_version
        self.dim = len(rows[0]["vector"]) if rows else 0

    @classmethod
    def build(cls, chunks: list[Chunk], encoder: Encoder, index_version: str) -> DenseIndex:
        vectors = encoder.embed_passages([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise DenseError("encoder returned a different number of vectors")
        rows = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            if len(vector) != encoder.dim:
                raise DenseError(f"vector dimension mismatch for {chunk.chunk_id}")
            rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "page": chunk.page,
                    "section": chunk.section,
                    "sensitivity": chunk.sensitivity,
                    "vector": [round(float(value), 6) for value in vector],
                }
            )
        return cls(rows, encoder.model_id, index_version)

    def save(self, path: Path) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "model_id": self.model_id,
            "index_version": self.index_version,
            "count": len(self.rows),
            "dim": self.dim,
        }
        lines = [json.dumps({"header": header}, ensure_ascii=False)]
        lines.extend(json.dumps(row, ensure_ascii=False) for row in self.rows)
        payload = "\n".join(lines) + "\n"
        path.write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return {"path": str(path), "sha256": digest, **header}

    @classmethod
    def load(cls, path: Path) -> DenseIndex:
        if not path.is_file():
            raise DenseError(f"dense index not found: {path}")
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            raise DenseError(f"dense index is empty: {path}")
        header = json.loads(lines[0]).get("header") or {}
        rows = [json.loads(line) for line in lines[1:]]
        if header.get("count") != len(rows):
            raise DenseError("dense index header count does not match its rows")
        return cls(rows, str(header.get("model_id")), str(header.get("index_version")))

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
        texts: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        if top_k <= 0 or not self.rows:
            return []
        ceiling = SENSITIVITY_ORDER.get(sensitivity_ceiling, -1)
        hits: list[SearchHit] = []
        for row in self.rows:
            if SENSITIVITY_ORDER.get(row["sensitivity"], 99) > ceiling:
                continue
            score = sum(
                left * right for left, right in zip(query_vector, row["vector"], strict=False)
            )
            if score > 0:
                chunk = Chunk(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    source_id=row["doc_id"],
                    page=int(row["page"]),
                    section=str(row["section"]),
                    text=(texts or {}).get(row["chunk_id"], ""),
                    token_count=0,
                    char_start=0,
                    char_end=0,
                    sensitivity=row["sensitivity"],
                )
                hits.append(SearchHit(chunk=chunk, score=score))
        hits.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id))
        return hits[:top_k]
