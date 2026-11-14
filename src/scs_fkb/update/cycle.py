"""Offline-safe update cycle: watch diff -> quality gate -> provisional plan.

The cycle never writes the register, the processed store or the index. It writes
a dated report and a plan under the run root for a human to review.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ..candidates import load_candidates, normalize_url
from ..config import REPO_ROOT
from ..registry import load_registry, validate_entry
from ..watch import run_watch
from .diff import changes_from_watch
from .provisional import ProvisionalError, plan_provisional
from .quality import assess_candidate

DEFAULT_REGISTRY = REPO_ROOT / "configs" / "corpus.yaml"
DEFAULT_CANDIDATES = REPO_ROOT / "configs" / "candidates.yaml"
DEFAULT_WATCH_CONFIG = REPO_ROOT / "configs" / "source-watch.yaml"


def _candidate_map(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        url = normalize_url(str(candidate.get("url") or ""))
        if url:
            mapped[url] = candidate
    return mapped


def _plan_one(
    change: Any,
    candidate: dict[str, Any],
    *,
    today: date,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    probe = {
        **candidate,
        "text_chars": change.text_chars or candidate.get("text_chars") or 0,
        "sha256": change.sha256 or candidate.get("sha256") or "",
        "reason": candidate.get("reason") or change.status,
    }
    quality = assess_candidate(probe)
    if not quality.passed:
        return None, {
            "watch_id": change.watch_id,
            "candidate_id": candidate.get("id"),
            "stage": "quality_rejected",
            "reasons": list(quality.reasons),
        }
    if not change.text_chars and not candidate.get("text_chars"):
        return None, {
            "watch_id": change.watch_id,
            "candidate_id": candidate.get("id"),
            "stage": "needs_fetch",
            "reasons": ["text_not_fetched"],
        }
    try:
        entry = plan_provisional(
            candidate,
            quality,
            today=today,
            license_value=str(candidate.get("license") or ""),
            sensitivity=str(candidate.get("sensitivity") or ""),
            practical_domain=str(candidate.get("practical_domain") or "other"),
            practical_personas=list(candidate.get("personas") or []),
            task_tags=list(candidate.get("task_tags") or []),
        )
    except ProvisionalError as exc:
        return None, {
            "watch_id": change.watch_id,
            "candidate_id": candidate.get("id"),
            "stage": "provisional_rejected",
            "reasons": [str(exc)],
        }
    errors = validate_entry(entry)
    if errors:
        return None, {
            "watch_id": change.watch_id,
            "candidate_id": candidate.get("id"),
            "stage": "validation_rejected",
            "reasons": errors,
        }
    return {
        "watch_id": change.watch_id,
        "candidate_id": candidate.get("id"),
        "entry": entry,
        "quality": quality.to_dict(),
    }, None


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Update cycle {summary['today']}",
        "",
        f"- Mode: `{summary['mode']}`",
        f"- Watch changes: {summary['changes']}",
        f"- Candidates matched: {summary['matched']}",
        f"- Provisional plans: {len(summary['plans'])}",
        f"- Rejected / needs fetch: {len(summary['rejected'])}",
        "",
        "| Watch id | Candidate | Stage | Reasons |",
        "|---|---|---|---|",
    ]
    for plan in summary["plans"]:
        lines.append(f"| {plan['watch_id']} | {plan['candidate_id']} | provisional | ok |")
    for row in summary["rejected"]:
        reasons = "; ".join(row.get("reasons") or [])
        lines.append(f"| {row['watch_id']} | {row['candidate_id']} | {row['stage']} | {reasons} |")
    lines.extend(
        [
            "",
            "No register, processed store or index was written. A provisional "
            "entry may answer only with a visible label and cannot alone support a "
            "rule, status, quantity or warning. Canonical promotion requires a "
            "human reviewer (see `promotion_draft`).",
        ]
    )
    return "\n".join(lines) + "\n"


def run_cycle(
    *,
    data_root: Path | str | None = None,
    run_root: Path | str,
    today: date | None = None,
    registry_path: Path | str = DEFAULT_REGISTRY,
    candidates_path: Path | str = DEFAULT_CANDIDATES,
    watch_config: Path | str = DEFAULT_WATCH_CONFIG,
    watch_report: dict[str, Any] | None = None,
    live: bool = False,
) -> dict[str, Any]:
    """Run one cycle and return the summary; writes only under the run root."""
    current = today or date.today()
    registry = load_registry(registry_path)
    candidates = load_candidates(candidates_path)
    if watch_report is None:
        baseline_path = None
        if data_root:
            baseline_path = Path(data_root).expanduser() / "watch" / "baseline.json"
        watch_report = run_watch(
            watch_config,
            offline=not live,
            baseline_path=baseline_path,
        )
    baseline: dict[str, str] = {}
    if data_root:
        baseline_path = Path(data_root).expanduser() / "watch" / "baseline.json"
        if baseline_path.is_file():
            try:
                baseline = {
                    str(key): str(value)
                    for key, value in (
                        json.loads(baseline_path.read_text(encoding="utf-8")).get("hashes") or {}
                    ).items()
                }
            except (OSError, json.JSONDecodeError):
                baseline = {}
    changes = changes_from_watch(watch_report, baseline)
    mapped = _candidate_map(candidates)
    plans: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    matched = 0
    for change in changes:
        candidate = mapped.get(normalize_url(change.url))
        if candidate is None:
            rejected.append(
                {
                    "watch_id": change.watch_id,
                    "candidate_id": "",
                    "stage": "no_candidate",
                    "reasons": ["changed page is not in the candidate queue"],
                }
            )
            continue
        matched += 1
        plan, failure = _plan_one(change, candidate, today=current)
        if plan is not None:
            plans.append(plan)
        if failure is not None:
            rejected.append(failure)
    summary: dict[str, Any] = {
        "today": current.isoformat(),
        "mode": "live" if live else "offline",
        "sources": len(registry),
        "candidates": len(candidates),
        "changes": len(changes),
        "matched": matched,
        "plans": plans,
        "rejected": rejected,
        "plan": {
            "provisional": plans,
            "rejected": rejected,
        },
    }
    output = Path(run_root).expanduser().resolve() / "update"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{current.isoformat()}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / f"{current.isoformat()}.md").write_text(_report(summary), encoding="utf-8")
    summary["report"] = str(output / f"{current.isoformat()}.md")
    return summary


__all__ = [
    "DEFAULT_CANDIDATES",
    "DEFAULT_REGISTRY",
    "DEFAULT_WATCH_CONFIG",
    "run_cycle",
]
