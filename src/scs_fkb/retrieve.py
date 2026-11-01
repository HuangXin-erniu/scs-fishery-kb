from __future__ import annotations

from collections.abc import Mapping

from .bm25 import BM25Index
from .fusion import reciprocal_rank_fusion
from .lexicon import expand_query
from .models import Chunk, SearchHit
from .text import tokenize


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        titles: Mapping[str, set[str]] | None = None,
        title_boost: float = 0.0,
        lexicon: list[dict[str, object]] | None = None,
        mode: str = "bm25",
        dense=None,
        encoder=None,
        fusion_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
    ) -> None:
        if mode not in {"bm25", "dense", "hybrid"}:
            raise ValueError(f"unknown retrieval mode: {mode}")
        if mode != "bm25" and (dense is None or encoder is None):
            raise ValueError("dense and hybrid modes need a dense index and an encoder")
        self.chunks = list(chunks)
        self.lexicon = list(lexicon or [])
        self.mode = mode
        self.dense = dense
        self.encoder = encoder
        self.fusion_k = fusion_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.texts = {chunk.chunk_id: chunk.text for chunk in self.chunks}
        self.index = BM25Index(self.chunks, titles=titles, title_boost=title_boost)

    def search(
        self,
        query: str,
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
    ) -> list[SearchHit]:
        expanded = expand_query(query, self.lexicon) if self.lexicon else query
        if self.mode == "bm25":
            return self.index.search(expanded, top_k=top_k, sensitivity_ceiling=sensitivity_ceiling)
        if self.mode == "dense":
            vector = self.encoder.embed_query(expanded)
            return self.dense.search(
                vector, top_k=top_k, sensitivity_ceiling=sensitivity_ceiling, texts=self.texts
            )
        depth = max(top_k, 10)
        lexical = self.index.search(expanded, top_k=depth, sensitivity_ceiling=sensitivity_ceiling)
        vector = self.encoder.embed_query(expanded)
        semantic = self.dense.search(
            vector, top_k=depth, sensitivity_ceiling=sensitivity_ceiling, texts=self.texts
        )
        return reciprocal_rank_fusion(
            [lexical, semantic],
            [self.bm25_weight, self.dense_weight],
            k=self.fusion_k,
            top_k=top_k,
        )

    def gate_ok(self, question: str, min_score: float, min_matched: int) -> bool:
        expanded = expand_query(question, self.lexicon) if self.lexicon else question
        top = self.index.search(expanded, top_k=1)
        return lexical_gate(question, top, min_score, min_matched)


def lexical_gate(
    question: str,
    bm25_hits: list,
    min_score: float,
    min_matched: int,
) -> bool:
    """The abstention gate: lexical evidence must exist in the BM25 top hit."""
    if not bm25_hits:
        return False
    query_tokens = set(tokenize(question))
    matched = len(query_tokens & set(tokenize(bm25_hits[0].chunk.text)))
    required = min(min_matched, len(query_tokens))
    return bm25_hits[0].score >= min_score and matched >= required
