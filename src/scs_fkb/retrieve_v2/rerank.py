from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3-int8"


class Reranker:
    """Cross-encoder reranker with a lazy optional backend."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER,
        cache_dir: str | None = None,
        *,
        max_candidates: int = 10,
        max_chars: int = 300,
        scorer: Callable[[str, Sequence[str]], Sequence[float]] | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.max_candidates = max_candidates
        self.max_chars = max_chars
        self._scorer = scorer
        self._model: Any = None

    def _score(self, query: str, texts: list[str]) -> list[float]:
        if self._scorer is not None:
            return [float(value) for value in self._scorer(query, texts)]
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(model_name=self.model_name, cache_dir=self.cache_dir)
        return [float(value) for value in self._model.rerank(query, texts)]

    def score_pairs(self, query: str, texts: Sequence[str]) -> list[float]:
        """Score query/text pairs directly, for callers that rank their own units."""
        return self._score(query, [text[: self.max_chars] for text in texts])

    def rerank(self, query: str, hits: list, top_k: int = 5) -> list:
        if not hits:
            return []
        candidates = hits[: self.max_candidates]
        texts = [hit.chunk.text[: self.max_chars] for hit in candidates]
        try:
            scores = self._score(query, texts)
        except Exception:  # noqa: BLE001 - optional model or network failure
            return hits[:top_k]
        ranked = sorted(
            zip(candidates, scores, strict=False),
            key=lambda item: (-item[1], item[0].chunk.chunk_id),
        )
        return [replace(hit, score=score) for hit, score in ranked[:top_k]]


__all__ = ["DEFAULT_RERANKER", "Reranker"]
