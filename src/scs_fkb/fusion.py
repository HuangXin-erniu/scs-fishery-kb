from __future__ import annotations

from .models import SearchHit


def reciprocal_rank_fusion(
    lists: list[list[SearchHit]],
    weights: list[float],
    k: int = 60,
    top_k: int = 5,
) -> list[SearchHit]:
    """Fuse ranked lists with weighted reciprocal-rank fusion."""
    if len(lists) != len(weights):
        raise ValueError("each ranked list needs a weight")
    scores: dict[str, float] = {}
    objects: dict[str, SearchHit] = {}
    for weight, hits in zip(weights, lists, strict=True):
        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)
            objects.setdefault(chunk_id, hit)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[:top_k]
    return [
        SearchHit(chunk=objects[chunk_id].chunk, score=scores[chunk_id]) for chunk_id in ordered
    ]
