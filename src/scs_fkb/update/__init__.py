"""Semi-automatic update loop: diff, quality gate, provisional plan and promotion."""

from __future__ import annotations

from .cycle import run_cycle
from .diff import Change, changes_from_watch
from .promote import PromotionError, promotion_draft
from .provisional import ProvisionalError, plan_provisional
from .quality import QualityReport, assess, assess_candidate

__all__ = [
    "Change",
    "PromotionError",
    "ProvisionalError",
    "QualityReport",
    "assess",
    "assess_candidate",
    "changes_from_watch",
    "plan_provisional",
    "promotion_draft",
    "run_cycle",
]
