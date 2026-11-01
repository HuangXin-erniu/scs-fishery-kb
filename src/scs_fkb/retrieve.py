from __future__ import annotations

from collections.abc import Mapping

from .bm25 import BM25Index
from .models import Chunk, SearchHit


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        titles: Mapping[str, set[str]] | None = None,
        title_boost: float = 0.0,
    ) -> None:
        self.chunks = list(chunks)
        self.index = BM25Index(self.chunks, titles=titles, title_boost=title_boost)

    def search(
        self,
        query: str,
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
    ) -> list[SearchHit]:
        return self.index.search(query, top_k=top_k, sensitivity_ceiling=sensitivity_ceiling)
