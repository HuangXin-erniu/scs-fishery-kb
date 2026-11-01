from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping

from .models import Chunk, SearchHit
from .text import tokenize

SENSITIVITY_ORDER = {"public": 0, "internal": 1, "restricted": 2, "unknown": 99}


class BM25Index:
    def __init__(
        self,
        chunks: list[Chunk],
        k1: float = 1.5,
        b: float = 0.75,
        titles: Mapping[str, set[str]] | None = None,
        title_boost: float = 0.0,
    ) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.titles = {key: set(value) for key, value in (titles or {}).items()}
        self.title_boost = title_boost
        self.doc_tokens = [tokenize(chunk.text) for chunk in self.chunks]
        self.doc_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.df: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            self.df.update(freqs.keys())
        self.doc_count = len(self.chunks)
        total_tokens = sum(len(tokens) for tokens in self.doc_tokens)
        self.avgdl = total_tokens / self.doc_count if self.doc_count else 0.0

    def search(
        self,
        query: str,
        top_k: int = 5,
        sensitivity_ceiling: str = "public",
    ) -> list[SearchHit]:
        if top_k <= 0 or not self.chunks or self.avgdl <= 0:
            return []
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return []
        ceiling = SENSITIVITY_ORDER.get(sensitivity_ceiling, -1)
        hits: list[SearchHit] = []
        for index, chunk in enumerate(self.chunks):
            if SENSITIVITY_ORDER.get(chunk.sensitivity, 99) > ceiling:
                continue
            score = self._score(index, query_tokens)
            if score > 0:
                if self.title_boost and self.titles:
                    title_tokens = self.titles.get(chunk.doc_id, set())
                    overlap = len(query_tokens & title_tokens) / len(query_tokens)
                    score *= 1.0 + self.title_boost * overlap
                hits.append(SearchHit(chunk=chunk, score=score))
        hits.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id))
        return hits[:top_k]

    def _score(self, index: int, query_tokens: set[str]) -> float:
        freqs = self.doc_freqs[index]
        doc_length = len(self.doc_tokens[index])
        score = 0.0
        for token in query_tokens:
            frequency = freqs.get(token, 0)
            if not frequency:
                continue
            idf = math.log(1.0 + (self.doc_count - self.df[token] + 0.5) / (self.df[token] + 0.5))
            denominator = frequency + self.k1 * (1.0 - self.b + self.b * doc_length / self.avgdl)
            score += idf * (frequency * (self.k1 + 1.0)) / denominator
        return score
