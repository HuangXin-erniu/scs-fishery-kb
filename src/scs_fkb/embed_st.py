from __future__ import annotations

from pathlib import Path


class SentenceTransformerEncoder:
    """Sentence-transformers adapter for models not supported by fastembed."""

    def __init__(self, model_id: str, cache_dir: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_id = model_id
        path = Path(cache_dir or "") / model_id.rsplit("/", 1)[-1]
        self.model = SentenceTransformer(str(path) if path.is_dir() else model_id, device="cpu")
        self.dim = int(self.model.get_sentence_embedding_dimension())

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            list(texts), normalize_embeddings=True, batch_size=16, show_progress_bar=False
        ).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_passages([text])[0]


__all__ = ["SentenceTransformerEncoder"]
