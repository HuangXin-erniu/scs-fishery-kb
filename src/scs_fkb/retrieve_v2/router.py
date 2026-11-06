from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..claims import classify, load_claims
from ..config import REPO_ROOT
from ..jurisdiction import question_jurisdiction
from .filters import RetrievalFilters

YEAR_RE = re.compile(r"(20\d{2})\s*年?")
FRESHNESS_WORDS = (
    "最新",
    "今年",
    "现在",
    "目前",
    "现行",
    "当前",
    "有效期",
    "是否有效",
    "台风",
    "预警",
    "开渔",
    "休渔",
    "禁渔",
    "休渔期",
    "截至",
)
REGION_WORDS = {
    "guangdong": ("广东", "粤"),
    "guangxi": ("广西", "桂"),
    "hainan": ("海南", "琼"),
    "fujian": ("福建", "闽"),
}


@dataclass(frozen=True)
class QueryPlan:
    question: str
    nature: str
    domain: str
    jurisdiction: str | None
    year: int | None
    region: str | None
    freshness: bool
    filters: RetrievalFilters


def _year(question: str, today: date) -> int | None:
    if "今年" in question or "本年" in question:
        return today.year
    matches = YEAR_RE.findall(question)
    return int(matches[-1]) if matches else None


def _region(question: str, jurisdiction: str | None) -> str | None:
    if jurisdiction and jurisdiction != "national":
        return jurisdiction
    for region, words in REGION_WORDS.items():
        if any(word in question for word in words):
            return region
    return None


def plan_query(
    question: str,
    *,
    claims_path: Path | None = None,
    today: date | None = None,
) -> QueryPlan:
    current = today or date.today()
    path = claims_path or (REPO_ROOT / "configs" / "claims.yaml")
    claims = load_claims(path) if path.is_file() else None
    claim = classify(question, claims) if claims else {"nature": "general", "domain": "general"}
    nature = str(claim.get("nature") or "general")
    domain = str(claim.get("domain") or "general")
    jurisdiction = question_jurisdiction(question)
    freshness = nature in {"status", "warning"} or any(word in question for word in FRESHNESS_WORDS)
    filters = RetrievalFilters(sensitivity_ceiling="public")
    return QueryPlan(
        question=question,
        nature=nature,
        domain=domain,
        jurisdiction=jurisdiction,
        year=_year(question, current),
        region=_region(question, jurisdiction),
        freshness=freshness,
        filters=filters,
    )


__all__ = ["FRESHNESS_WORDS", "QueryPlan", "REGION_WORDS", "plan_query"]
