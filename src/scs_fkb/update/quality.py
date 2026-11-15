"""Quality gate for a changed page before it may enter the provisional tier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_LICENSES = frozenset({"public", "internal", "licensed", "cc-by-nc-sa-3.0-igo"})
ALLOWED_SENSITIVITIES = frozenset({"public", "internal", "restricted"})
MIN_TEXT_CHARS = 200
MIN_TEXT_COVERAGE = 0.5


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    reasons: tuple[str, ...] = ()
    text_chars: int = 0
    text_coverage: float = 0.0
    parseable: bool = False
    license: str = ""
    sensitivity: str = ""
    duplicate: bool = False
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "text_chars": self.text_chars,
            "text_coverage": self.text_coverage,
            "parseable": self.parseable,
            "license": self.license,
            "sensitivity": self.sensitivity,
            "duplicate": self.duplicate,
            "content_hash": self.content_hash,
        }


def assess(
    *,
    text_chars: int,
    parseable: bool,
    license_value: str,
    sensitivity_value: str,
    content_hash: str = "",
    seen_hashes: set[str] | None = None,
    reason: str = "changed",
    license_note: str = "",
) -> QualityReport:
    """Apply the provisional-tier rules; a failure is a recorded reason, not an exception."""
    reasons: list[str] = []
    licenses = str(license_value or "").strip()
    sensitivity = str(sensitivity_value or "").strip()
    if not parseable:
        reasons.append("not_parseable")
    if int(text_chars) < MIN_TEXT_CHARS:
        reasons.append("text_too_short")
    if licenses not in ALLOWED_LICENSES:
        reasons.append("license_unknown")
    if licenses == "licensed" and not str(license_note or "").strip():
        reasons.append("licensed_without_note")
    if sensitivity not in ALLOWED_SENSITIVITIES:
        reasons.append("sensitivity_unknown")
    duplicate = bool(content_hash) and content_hash in (seen_hashes or set())
    if duplicate and reason != "supersede":
        reasons.append("duplicate_content")
    coverage = min(1.0, max(0.0, int(text_chars) / float(MIN_TEXT_CHARS * 5)))
    if coverage < MIN_TEXT_COVERAGE:
        reasons.append("text_coverage_low")
    return QualityReport(
        passed=not reasons,
        reasons=tuple(reasons),
        text_chars=int(text_chars),
        text_coverage=round(coverage, 3),
        parseable=parseable,
        license=licenses,
        sensitivity=sensitivity,
        duplicate=duplicate,
        content_hash=str(content_hash or ""),
    )


def assess_candidate(
    candidate: dict[str, Any], *, seen_hashes: set[str] | None = None
) -> QualityReport:
    """Convenience wrapper for candidate drafts that carry the probe fields."""
    return assess(
        text_chars=int(candidate.get("text_chars") or 0),
        parseable=bool(candidate.get("parseable") or False),
        license_value=str(candidate.get("license") or ""),
        sensitivity_value=str(candidate.get("sensitivity") or ""),
        content_hash=str(candidate.get("sha256") or ""),
        seen_hashes=seen_hashes,
        reason=str(candidate.get("reason") or "changed"),
        license_note=str(candidate.get("license_note") or ""),
    )


__all__ = [
    "ALLOWED_LICENSES",
    "ALLOWED_SENSITIVITIES",
    "MIN_TEXT_CHARS",
    "QualityReport",
    "assess",
    "assess_candidate",
]
