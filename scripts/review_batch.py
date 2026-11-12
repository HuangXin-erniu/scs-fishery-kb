#!/usr/bin/env python3
"""Summarise the candidate queue for a human licence/authority review.

Reads `configs/candidates.yaml` and, optionally, the Phase 0 survey JSONL. It
writes a triage table under the run root; it never fetches, registers or promotes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scs_fkb.candidates import load_candidates


def _survey(path: str) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    source = Path(path).expanduser()
    if not source.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        url = str(row.get("url") or "").rstrip("/")
        if url:
            rows[url] = row
    return rows


def _missing(row: dict[str, Any], probe: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not probe.get("sha256"):
        missing.append("sha256")
    if not probe.get("license"):
        missing.append("license")
    if not probe.get("sensitivity"):
        missing.append("sensitivity")
    if int(probe.get("text_chars") or 0) < 200:
        missing.append("text_chars<200")
    if probe.get("status") not in (200, "200"):
        missing.append("unreachable")
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default="configs/candidates.yaml")
    parser.add_argument("--survey", default="")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    candidates = load_candidates(args.candidates)
    survey = _survey(args.survey)
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        url = str(candidate.get("url") or "").rstrip("/")
        probe = survey.get(url) or {}
        missing = _missing(candidate, probe)
        rows.append(
            {
                "id": candidate.get("id"),
                "title": candidate.get("title"),
                "tier": candidate.get("proposed_tier"),
                "class": candidate.get("proposed_class"),
                "status": probe.get("status"),
                "text_chars": probe.get("text_chars"),
                "license_hint": probe.get("license_hint", "unknown"),
                "freshness": probe.get("freshness_hint") or [],
                "missing": missing,
                "ready": not missing,
            }
        )
    lines = [
        "# Practical-source candidate triage",
        "",
        f"- Candidates: {len(rows)}",
        f"- Ready for a provisional review package: {sum(1 for row in rows if row['ready'])}",
        f"- Need licence/hash/sensitivity/parseability work: "
        f"{sum(1 for row in rows if not row['ready'])}",
        "",
        "| ID | Source | Tier | HTTP | Text | Licence hint | Missing |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {str(row['title'])[:40]} | {row['tier']} | "
            f"{row['status']} | {row['text_chars'] or ''} | {row['license_hint']} | "
            f"{', '.join(row['missing']) or '—'} |"
        )
    lines.extend(
        [
            "",
            "A row marked ready still needs a human licence/authority decision and a "
            "captured document URL; the tooling never fetches or registers.",
        ]
    )
    report = "\n".join(lines) + "\n"
    if args.out:
        path = Path(args.out).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"report: {path}")
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif not args.out:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
