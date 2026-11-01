from __future__ import annotations

from .bm25 import BM25Index
from .models import Chunk, SearchHit


class Retriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = list(chunks)
        self.index = BM25Index(self.chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
    ) -> list[SearchHit]:
        return self.index.search(query, top_k=top_k, sensitivity_ceiling=sensitivity_ceiling)
