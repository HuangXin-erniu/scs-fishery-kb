from __future__ import annotations

from typing import Any

from llama_index.core.embeddings import BaseEmbedding
from pydantic import PrivateAttr

from ..embed import DEFAULT_MODEL, FastEmbedEncoder


class EncoderEmbedding(BaseEmbedding):
    """Thin LlamaIndex adapter over the project's encoder protocol."""

    _encoder: Any = PrivateAttr()

    def __init__(self, encoder: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._encoder = encoder

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._encoder.embed_query(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._encoder.embed_passages([text])[0]


def build_encoder(model_name: str = DEFAULT_MODEL, cache_dir: str | None = None) -> Any:
    """Return the local encoder for the configured model."""
    return FastEmbedEncoder(model_name=model_name, cache_dir=cache_dir)


__all__ = ["DEFAULT_MODEL", "EncoderEmbedding", "build_encoder"]
