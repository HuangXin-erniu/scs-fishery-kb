from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..bm25 import BM25Index
from ..config import DEFAULT_LEXICON
from ..fusion import reciprocal_rank_fusion
from ..lexicon import expand_query, load_lexicon
from ..models import Chunk, SearchHit
from ..retrieve import lexical_gate
from ..text import tokenize
from .filters import RetrievalFilters, filter_hits
from .rerank import DEFAULT_RERANKER, Reranker


def _title_tokens(documents: list[dict[str, Any]]) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = {}
    for document in documents:
        title = document.get("title_zh") or document.get("title") or ""
        titles[str(document["doc_id"])] = set(tokenize(title))
    return titles


class HybridRetriever:
    """BM25 + dense retrieval, RRF, metadata filters and optional reranking."""

    def __init__(
        self,
        chunks: list[Chunk],
        bm25: BM25Index,
        *,
        dense_index: Any = None,
        encoder: Any = None,
        dense_fn: Callable[[str, int], list[tuple[str, float]]] | None = None,
        reranker: Reranker | None = None,
        lexicon: list[dict[str, object]] | None = None,
        depth: int = 10,
        fusion_k: int = 60,
        bm25_weight: float = 2.0,
        dense_weight: float = 1.0,
    ) -> None:
        self.chunks = list(chunks)
        self.by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        self.bm25 = bm25
        self.dense_index = dense_index
        self.encoder = encoder
        self.dense_fn = dense_fn
        self.reranker = reranker
        self.lexicon = list(lexicon or [])
        self.depth = depth
        self.fusion_k = fusion_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def _dense_hits(self, query: str, ceiling: str) -> list[SearchHit]:
        if self.dense_fn is not None:
            pairs = self.dense_fn(query, self.depth)
        elif self.dense_index is not None and self.encoder is not None:
            from ..index_v2 import dense_search

            pairs = dense_search(self.dense_index, query, top_k=self.depth)
        else:
            return []
        hits: list[SearchHit] = []
        for chunk_id, score in pairs:
            chunk = self.by_id.get(chunk_id)
            if chunk is None:
                continue
            if chunk.sensitivity not in {"public"} and ceiling == "public":
                continue
            hits.append(SearchHit(chunk=chunk, score=score))
        return hits

    def search(
        self,
        question: str,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
        *,
        rerank: bool = True,
    ) -> list[SearchHit]:
        ceiling = (filters or RetrievalFilters()).sensitivity_ceiling
        expanded = expand_query(question, self.lexicon) if self.lexicon else question
        lexical = self.bm25.search(expanded, top_k=self.depth, sensitivity_ceiling=ceiling)
        dense = self._dense_hits(expanded, ceiling)
        fused = reciprocal_rank_fusion(
            [lexical, dense],
            [self.bm25_weight, self.dense_weight],
            k=self.fusion_k,
            top_k=self.depth,
        )
        fused = filter_hits(fused, filters)
        if rerank and self.reranker is not None:
            fused = self.reranker.rerank(question, fused, top_k=max(top_k, 5))
        return fused[:top_k]

    def search_queries(
        self,
        queries: list[str],
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> list[SearchHit]:
        """Fuse several phrasings of the same question with RRF."""
        unique = [item.strip() for item in dict.fromkeys(queries) if item and item.strip()]
        if not unique:
            return []
        lists = [
            self.search(query, top_k=max(top_k, 10), filters=filters, rerank=False)
            for query in unique
        ]
        if len(lists) == 1:
            return lists[0][:top_k]
        return reciprocal_rank_fusion(lists, [1.0] * len(lists), top_k=top_k)

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        expanded = expand_query(question, self.lexicon) if self.lexicon else question
        top = self.bm25.search(expanded, top_k=1)
        return lexical_gate(question, top, min_score, min_matched)


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def build_retriever(
    data_root: Path | str,
    *,
    model_name: str = "BAAI/bge-small-zh-v1.5",
    reranker: bool = False,
    reranker_model: str = DEFAULT_RERANKER,
) -> HybridRetriever:
    from ..embed import FastEmbedEncoder
    from ..index_v2 import load_chunks_v2, open_index

    root = Path(data_root).expanduser().resolve()
    chunks = load_chunks_v2(root)
    documents = _rows(root / "v2" / "processed" / "documents.jsonl")
    encoder = FastEmbedEncoder(model_name=model_name, cache_dir=str(root / "embeddings" / "models"))
    dense_index = open_index(root, encoder)
    bm25 = BM25Index(
        chunks,
        titles=_title_tokens(documents),
        title_boost=1.0,
    )
    reranker_obj = (
        Reranker(reranker_model, cache_dir=str(root / "embeddings" / "models"))
        if reranker
        else None
    )
    lexicon = load_lexicon(DEFAULT_LEXICON) if DEFAULT_LEXICON.is_file() else []
    return HybridRetriever(
        chunks,
        bm25,
        dense_index=dense_index,
        encoder=encoder,
        reranker=reranker_obj,
        lexicon=lexicon,
    )


__all__ = ["HybridRetriever", "build_retriever"]
