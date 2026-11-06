from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..bm25 import SENSITIVITY_ORDER
from ..models import Chunk


@dataclass(frozen=True)
class RetrievalFilters:
    sensitivity_ceiling: str = "public"
    authority_tiers: tuple[str, ...] = ()
    levels: tuple[str, ...] = ()
    jurisdictions: tuple[str, ...] = ()
    as_of: str | None = None

    def matches(self, chunk: Chunk) -> bool:
        ceiling = SENSITIVITY_ORDER.get(self.sensitivity_ceiling, -1)
        if SENSITIVITY_ORDER.get(chunk.sensitivity, 99) > ceiling:
            return False
        if self.authority_tiers and chunk.authority_tier not in self.authority_tiers:
            return False
        if self.levels and chunk.level not in self.levels:
            return False
        if self.jurisdictions and chunk.jurisdiction not in self.jurisdictions:
            return False
        if self.as_of:
            try:
                point = date.fromisoformat(self.as_of)
            except ValueError:
                return False
            if chunk.effective_from:
                try:
                    if date.fromisoformat(chunk.effective_from) > point:
                        return False
                except ValueError:
                    return False
            if chunk.effective_to:
                try:
                    if date.fromisoformat(chunk.effective_to) < point:
                        return False
                except ValueError:
                    return False
        return True


def filter_hits(hits: list, filters: RetrievalFilters | None) -> list:
    if filters is None:
        return hits
    return [hit for hit in hits if filters.matches(hit.chunk)]


__all__ = ["RetrievalFilters", "filter_hits"]
