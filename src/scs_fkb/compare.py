from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .dense import DenseIndex, embeddings_dir, index_path
from .embed import DEFAULT_MODEL, FastEmbedEncoder
from .evaluate import evaluate, title_tokens
from .ingest import load_pipeline
from .lexicon import load_lexicon
from .retrieve import Retriever
from .store import load_chunks


def _timed(retriever: Retriever, question: str) -> tuple[list[Any], float]:
    start = time.perf_counter()
    hits = retriever.search(question, top_k=5)
    return hits, (time.perf_counter() - start) * 1000


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)) - 1)], 2)


def run_comparison(
    data_root: Path,
    questions_path: Path,
    anchors_path: Path,
    pipeline_path: Path,
    lexicon_path: Path,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    chunks, manifest = load_chunks(data_root)
    pipeline = load_pipeline(pipeline_path)
    retrieval = pipeline.get("retrieval") or {}
    answer = pipeline.get("answer") or {}
    lexicon = load_lexicon(lexicon_path)
    version = str(manifest.get("index_version"))
    title_boost = float(retrieval.get("title_boost", 0.0))
    min_score = float(answer.get("min_score", 0.0))
    min_matched = int(answer.get("min_matched", 3))

    dense_index = DenseIndex.load(index_path(data_root, model, version))
    encoder = FastEmbedEncoder(model, cache_dir=str(embeddings_dir(data_root) / "models"))

    def retriever(mode: str, use_lexicon: bool) -> Retriever:
        return Retriever(
            chunks,
            titles=titles,
            title_boost=title_boost,
            lexicon=lexicon if use_lexicon else None,
            mode=mode,
            dense=dense_index if mode != "bm25" else None,
            encoder=encoder if mode != "bm25" else None,
            fusion_k=int(retrieval.get("fusion_k", 60)),
            bm25_weight=float(retrieval.get("bm25_weight", 1.0)),
            dense_weight=float(retrieval.get("dense_weight", 1.0)),
        )

    titles = title_tokens(manifest["documents"])
    arms = {
        "bm25": retriever("bm25", False),
        "bm25_lexicon": retriever("bm25", True),
        "dense": retriever("dense", False),
        "hybrid": retriever("hybrid", True),
    }
    report: dict[str, Any] = {"index_version": version, "model": model, "arms": {}}
    for name, arm in arms.items():
        latencies: list[float] = []

        def searcher(question: str, arm=arm, latencies=latencies) -> list[Any]:
            hits, elapsed = _timed(arm, question)
            latencies.append(elapsed)
            return hits

        if name in {"bm25", "bm25_lexicon"}:
            result = evaluate(
                questions_path,
                anchors_path,
                data_root,
                min_score=min_score,
                min_matched=min_matched,
                top_k=5,
                title_boost=title_boost,
                lexicon=lexicon if name == "bm25_lexicon" else [],
            )
        else:
            result = evaluate(
                questions_path,
                anchors_path,
                data_root,
                min_score=min_score,
                min_matched=min_matched,
                top_k=5,
                title_boost=title_boost,
                lexicon=[],
                searcher=searcher,
                gate=lambda question, arm=arm: arm.gate_ok(question, min_score, min_matched),
            )
            result["summary"]["p95_latency_ms"] = _p95(latencies)
        report["arms"][name] = result["summary"]
        if name == "bm25":
            report["reference"] = result["reference"]
            report["reference_summary"] = {
                key: value
                for key, value in result["summary"].items()
                if key.startswith("reference_")
            }
            report["statistics"] = result["statistics"]
            report["statistics_summary"] = {
                key: value
                for key, value in result["summary"].items()
                if key.startswith("statistics_")
            }
    return report
