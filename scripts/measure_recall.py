#!/usr/bin/env python3
"""Measure expected-document recall over the acceptance questions.

For every answerable question the script asks whether any document the instrument
expects appears in the top-k results, comparing BM25, dense and hybrid retrieval.
This separates chunking and embedding quality from answer generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_MODELS = ["BAAI/bge-small-zh-v1.5"]


def _chunks(data_root: Path, *, label: bool = True, path: str = "") -> list[Any]:
    from scs_fkb.models import Chunk

    source = Path(path) if path else data_root / "v2/processed/chunks.jsonl"
    rows = [json.loads(line) for line in source.open(encoding="utf-8") if line.strip()]
    chunks = [
        Chunk(
            chunk_id=row["chunk_id"],
            doc_id=row["doc_id"],
            source_id=row.get("source_id") or "",
            page=int(row.get("page") or 0),
            section=row.get("section") or "",
            text=row["text"],
            token_count=int(row.get("token_count") or 0),
            char_start=int(row.get("char_start") or 0),
            char_end=int(row.get("char_end") or 0),
            sensitivity=row.get("sensitivity") or "public",
        )
        for row in rows
    ]
    if label:
        from scs_fkb.ingest_v2.chunking import label_sections

        chunks = label_sections(chunks)
    return chunks


def _docmap(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))["mapping"]


def _expected(row: dict[str, Any], docmap: dict[str, Any], indexed: set[str]) -> set[str]:
    docs: set[str] = set()
    for source_id in row["scs_doc_ids"]:
        entry = docmap.get(source_id) or {}
        if entry.get("covers") in ("full", "partial"):
            docs |= set(entry.get("docs") or [])
    return docs & indexed


def _embed_chunks(encoder: Any, chunks: list[Any], cache_dir: Path, tag: str) -> Any:
    import numpy as np

    digest = hashlib.sha256(
        "\n".join(f"{chunk.chunk_id}\t{chunk.text}" for chunk in chunks).encode()
    ).hexdigest()[:16]
    cache = cache_dir / f"{tag}-{digest}.npy"
    if cache.is_file():
        return np.load(cache)
    started = time.perf_counter()
    vectors = encoder.embed_passages([chunk.text for chunk in chunks])
    matrix = np.asarray(vectors, dtype="float32")
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache, matrix)
    print(
        f"{tag}: embedded {len(chunks)} chunks in {time.perf_counter() - started:.1f}s",
        file=sys.stderr,
    )
    return matrix


def _rank(matrix: Any, queries: list[str], encoder: Any, top_k: int) -> list[int]:
    import numpy as np

    scores = np.zeros(matrix.shape[0], dtype="float32")
    for query in queries:
        q = np.asarray(encoder.embed_query(query), dtype="float32")
        scores = np.maximum(scores, matrix @ q)
    return list(np.argsort(-scores)[:top_k])


def _recall(
    rows: list[dict[str, Any]],
    docmap: dict[str, Any],
    chunks: list[Any],
    matrix: Any,
    encoder: Any,
    bm25: Any,
    *,
    top_k: int,
    queries_by_question: dict[str, list[str]] | None = None,
    reranker: Any = None,
) -> dict[str, Any]:
    from scs_fkb.fusion import reciprocal_rank_fusion
    from scs_fkb.models import SearchHit

    indexed = {chunk.doc_id for chunk in chunks}
    doc_ids = [chunk.doc_id for chunk in chunks]
    hits = {"dense": 0, "bm25": 0, "hybrid": 0, "reranked": 0}
    totals = 0
    per_domain: dict[str, list[int]] = {}
    latency = 0.0
    for row in rows:
        expected = _expected(row, docmap, indexed)
        if not expected:
            continue
        question = str(row["question"])
        queries = [question]
        if queries_by_question is not None:
            queries += [item for item in queries_by_question.get(row["id"], []) if item]
        started = time.perf_counter()
        dense_idx = _rank(matrix, queries, encoder, max(top_k, 20))
        lexical = []
        for query in queries:
            lexical.extend(bm25.search(query, top_k=max(top_k, 20)))
        lexical.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id))
        lexical = lexical[: max(top_k, 20)]
        fused = reciprocal_rank_fusion(
            [
                [SearchHit(chunk=chunks[index], score=1.0) for index in dense_idx],
                lexical,
            ],
            [1.0, 1.0],
            top_k=max(top_k, 20),
        )
        latency += time.perf_counter() - started
        dense_order = [doc_ids[index] for index in dense_idx]
        lexical_order = [hit.chunk.doc_id for hit in lexical]
        hybrid_order = [hit.chunk.doc_id for hit in fused]
        ranked = hybrid_order
        if reranker is not None:
            started = time.perf_counter()
            ranked_hits = reranker.rerank(question, fused, top_k=top_k)
            ranked = [hit.chunk.doc_id for hit in ranked_hits]
            latency += time.perf_counter() - started
        totals += 1
        for mode, order in (
            ("dense", dense_order),
            ("bm25", lexical_order),
            ("hybrid", hybrid_order),
            ("reranked", ranked),
        ):
            ok = int(bool(set(order) & expected))
            hits[mode] += ok
            per_domain.setdefault(row["domain"], []).append(ok)
    count = max(1, totals)
    return {
        "questions": count,
        "recall": {mode: round(value / count, 4) for mode, value in hits.items()},
        "top_k": top_k,
        "mean_latency_ms": round(1000 * latency / count, 1),
        "per_domain": {
            domain: round(sum(values) / len(values), 4)
            for domain, values in sorted(per_domain.items())
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--out", default="")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-labels", action="store_true", help="keep empty sections")
    parser.add_argument("--chunks", default="", help="chunk JSONL override")
    parser.add_argument("--rewrite", action="store_true", help="rewrite queries with the model")
    parser.add_argument("--rerank", action="store_true", help="rerank fused candidates")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    if not args.data_root:
        print("set --data-root or SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    data_root = Path(args.data_root).expanduser().resolve()

    dataset = [
        json.loads(line)
        for line in (data_root / "eval/acceptance/dataset.jsonl").open(encoding="utf-8")
    ]
    rows = [row for row in dataset if row["answerability"] in ("可答", "部分可答")]
    docmap = _docmap(data_root / "eval/acceptance/doc-map.yaml")
    chunks = _chunks(data_root, label=not args.no_labels, path=args.chunks)

    from scs_fkb.bm25 import BM25Index

    bm25 = BM25Index(chunks)
    queries_by_question: dict[str, list[str]] = {}
    if args.rewrite:
        from concurrent.futures import ThreadPoolExecutor

        from scs_fkb.llm import LLMClient, LLMConfig, LLMError
        from scs_fkb.rag import LLMCache
        from scs_fkb.retrieve_v2.rewrite import rewrite

        try:
            config = LLMConfig.from_env()
        except LLMError as exc:
            print(f"rewrite unavailable: {exc}", file=sys.stderr)
        else:
            client = LLMClient(config)
            cache = LLMCache(data_root / "llm-cache")

            def work(row: dict[str, Any]) -> tuple[str, list[str]]:
                return row["id"], rewrite(str(row["question"]), client, cache)

            with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
                for row_id, queries in pool.map(work, rows):
                    queries_by_question[row_id] = queries
            print(f"rewrote {len(queries_by_question)} questions", file=sys.stderr)
    reranker = None
    if args.rerank:
        from scs_fkb.retrieve_v2.rerank import Reranker

        reranker = Reranker(cache_dir=str(data_root / "embeddings" / "models"))
    results: dict[str, Any] = {"chunks": len(chunks), "questions": len(rows), "models": {}}
    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        from scs_fkb.embed import FastEmbedEncoder

        started = time.perf_counter()
        encoder = FastEmbedEncoder(
            model_name=model, cache_dir=str(data_root / "embeddings" / "models")
        )
        load_seconds = time.perf_counter() - started
        matrix = _embed_chunks(
            encoder, chunks, data_root / "embeddings" / "recall", model.replace("/", "-")
        )
        per_model = _recall(
            rows,
            docmap,
            chunks,
            matrix,
            encoder,
            bm25,
            top_k=args.top_k,
            queries_by_question=queries_by_question or None,
            reranker=reranker,
        )
        per_model["load_seconds"] = round(load_seconds, 1)
        per_model["dim"] = int(getattr(encoder, "dim", 0))
        results["models"][model] = per_model
        print(json.dumps({model: per_model}, ensure_ascii=False))

    out = (
        Path(args.out)
        if args.out
        else Path(os.environ.get("SCS_FKB_RUN_ROOT", ".")) / "P11-IDX-175"
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "recall.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Retrieval recall", "", f"Chunks: {len(chunks)}; questions: {len(rows)}", ""]
    lines.append("| Model | Dim | Dense | BM25 | Hybrid | Latency ms |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for model, value in results["models"].items():
        lines.append(
            f"| {model} | {value['dim']} | {value['recall']['dense']} | "
            f"{value['recall']['bm25']} | {value['recall']['hybrid']} | "
            f"{value['mean_latency_ms']} |"
        )
    (out / "recall.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
