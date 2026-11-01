from __future__ import annotations

from collections.abc import Mapping

from .bm25 import BM25Index
from .lexicon import expand_query
from .models import Chunk, SearchHit


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        titles: Mapping[str, set[str]] | None = None,
        title_boost: float = 0.0,
        lexicon: list[dict[str, object]] | None = None,
    ) -> None:
        self.chunks = list(chunks)
        self.lexicon = list(lexicon or [])
        self.index = BM25Index(self.chunks, titles=titles, title_boost=title_boost)

    def search(
        self,
        query: str,
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
    ) -> list[SearchHit]:
        expanded = expand_query(query, self.lexicon) if self.lexicon else query
        return self.index.search(expanded, top_k=top_k, sensitivity_ceiling=sensitivity_ceiling)
