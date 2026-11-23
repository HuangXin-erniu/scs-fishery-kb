"""Lightweight document-level reranking for Track B evaluation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

DEFAULT_WEIGHTS = (0.6, 0.0, 0.2, 0.2)


def _bigrams(text: str) -> set[str]:
    return {text[i : i + 2] for i in range(len(text) - 1)} - {"  "}


def _jaccard(left: str, right: str) -> float:
    a, b = _bigrams(left), _bigrams(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def rank_documents(
    question: str,
    hits: list[Any],
    documents: dict[str, dict[str, Any]] | None = None,
    *,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """Aggregate chunks to documents and rank by fused/section/number features."""
    grouped: dict[str, list[Any]] = defaultdict(list)
    for hit in hits:
        grouped[hit.chunk.doc_id].append(hit)
    documents = documents or {}
    digits = [token for token in __import__("re").findall(r"\d+", question)]
    scored: list[tuple[str, float]] = []
    for doc_id, doc_hits in grouped.items():
        doc_hits.sort(key=lambda hit: -hit.score)
        fused = sum(hit.score for hit in doc_hits[:3])
        title = str(documents.get(doc_id, {}).get("title") or "")
        title_score = _jaccard(question, title)
        section_score = max(
            (_jaccard(question, hit.chunk.section) for hit in doc_hits), default=0.0
        )
        body = " ".join(hit.chunk.text for hit in doc_hits[:3])
        number_score = 1.0 if digits and any(token in body for token in digits) else 0.0
        score = (
            weights[0] * fused
            + weights[1] * title_score
            + weights[2] * section_score
            + weights[3] * number_score
        )
        scored.append((doc_id, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:top_k]


__all__ = ["DEFAULT_WEIGHTS", "rank_documents"]
