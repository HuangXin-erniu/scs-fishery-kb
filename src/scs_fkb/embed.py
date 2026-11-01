from __future__ import annotations

import hashlib
import math
from typing import Protocol

DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


class Encoder(Protocol):
    model_id: str
    dim: int

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class HashingEncoder:
    """Deterministic stand-in used by tests so CI never downloads a model."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self.model_id = f"hashing-{dim}"

    def _encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = [text[index : index + 2] for index in range(max(len(text) - 1, 0))] or [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _normalize(vector)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._encode(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._encode(text)


class FastEmbedEncoder:
    """ONNX BGE encoder; fastembed is imported lazily so CI needs no model."""

    def __init__(self, model_name: str = DEFAULT_MODEL, cache_dir: str | None = None) -> None:
        from fastembed import TextEmbedding

        self.model_id = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self.dim = int(self._model.embedding_size)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.passage_embed(texts)
        return [_normalize([float(value) for value in vector]) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._model.query_embed(text)))
        return _normalize([float(value) for value in vector])
