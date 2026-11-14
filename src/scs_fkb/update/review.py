"""Review package for a practical-source candidate.

The operator fetches and inspects the page, supplies the observed text length,
hash, licence and sensitivity, and gets a provisional entry plus the actions
that still need a human. No network call and no register write happens here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .provisional import ProvisionalError, plan_provisional
from .quality import QualityReport, assess

REVIEW_ACTIONS = (
    "inspect_page_and_licence",
    "capture_snapshot_under_data_root",
    "register_provisional_entry",
    "rebuild_processed_and_index",
    "run_regression",
    "human_review_to_canonical_or_reject",
)


@dataclass(frozen=True)
class ReviewPackage:
    candidate_id: str
    quality: QualityReport
    entry: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    actions: tuple[str, ...] = REVIEW_ACTIONS

    @property
    def acceptable(self) -> bool:
        return self.quality.passed and self.entry is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "acceptable": self.acceptable,
            "quality": self.quality.to_dict(),
            "entry": self.entry,
            "warnings": list(self.warnings),
            "actions": list(self.actions),
        }


def review_candidate(
    candidate: dict[str, Any],
    *,
    text_chars: int,
    sha256: str,
    license_value: str,
    sensitivity: str,
    practical_domain: str = "other",
    today: date | None = None,
    source_id: str = "",
) -> ReviewPackage:
    current = today or date.today()
    quality = assess(
        text_chars=text_chars,
        parseable=True,
        license_value=license_value,
        sensitivity_value=sensitivity,
        content_hash=sha256,
        reason=str(candidate.get("reason") or "changed"),
        license_note=str(candidate.get("license_note") or ""),
    )
    warnings: list[str] = []
    if not quality.passed:
        return ReviewPackage(
            candidate_id=str(candidate.get("id") or ""),
            quality=quality,
            warnings=tuple(quality.reasons),
        )
    if not str(candidate.get("proposed_level") or ""):
        warnings.append("proposed_level was not set; derived from the authority tier")
    try:
        entry = plan_provisional(
            candidate,
            quality,
            today=current,
            source_id=source_id,
            license_value=license_value,
            sensitivity=sensitivity,
            practical_domain=practical_domain,
        )
    except ProvisionalError as exc:
        return ReviewPackage(
            candidate_id=str(candidate.get("id") or ""),
            quality=quality,
            warnings=tuple(list(warnings) + [str(exc)]),
        )
    return ReviewPackage(
        candidate_id=str(candidate.get("id") or ""),
        quality=quality,
        entry=entry,
        warnings=tuple(warnings),
    )


__all__ = ["REVIEW_ACTIONS", "ReviewPackage", "review_candidate"]
