#!/usr/bin/env python3
"""Offline gate for source registry, currency, watch coverage and candidates.

CI runs this with the real date. It never opens a socket: the watch list is read
as configuration, and only the recorded statuses are inspected.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from scs_fkb.candidates import CandidateError, check_candidates, load_candidates
from scs_fkb.config import REPO_ROOT
from scs_fkb.registry import (
    RegistryError,
    check_currency,
    load_registry,
    validate_watch_coverage,
)
from scs_fkb.watch import WatchError, load_watch

DEFAULT_REGISTRY = REPO_ROOT / "configs" / "corpus.yaml"
DEFAULT_WATCH = REPO_ROOT / "configs" / "source-watch.yaml"
DEFAULT_CANDIDATES = REPO_ROOT / "configs" / "candidates.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--grace-days", type=int, default=30)
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--watch", default=str(DEFAULT_WATCH))
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    try:
        registry = load_registry(Path(args.registry))
    except RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 1
    try:
        watch = load_watch(Path(args.watch))
        watch_ids = [str(item["id"]) for item in watch["sources"]]
        validate_watch_coverage(registry, watch["sources"])
        watch_error = ""
    except (WatchError, RegistryError) as exc:
        watch_ids = []
        watch_error = str(exc)
        errors.append(watch_error)

    try:
        today = date.fromisoformat(args.today)
    except ValueError:
        print(f"invalid --today: {args.today}", file=sys.stderr)
        return 2
    currency = check_currency(registry, today=today, grace_days=args.grace_days)
    errors.extend(currency["errors"])
    overdue = currency["overdue"]

    candidate_summary: dict[str, object] = {}
    try:
        candidates = load_candidates(Path(args.candidates))
        candidate_summary = check_candidates(
            Path(args.candidates),
            today=today,
            registry_ids=set(registry),
        )
        errors.extend(candidate_summary.get("errors") or [])
        expired = candidate_summary.get("expired") or []
        if expired:
            errors.append(f"{len(expired)} open candidate(s) past their expiry")
    except CandidateError as exc:
        errors.append(f"candidate error: {exc}")
        candidates = []

    active = sum(1 for item in registry.values() if item.get("lifecycle") == "active")
    provisional = [
        source_id
        for source_id, item in registry.items()
        if (item.get("ingest") or {}).get("tier") == "provisional"
    ]
    result = {
        "today": today.isoformat(),
        "sources": len(registry),
        "active": active,
        "provisional": provisional,
        "overdue": overdue,
        "watch_entries": len(watch_ids),
        "watch_coverage": "ok" if not watch_error else "failed",
        "watch_error": watch_error,
        "candidates": len(candidates),
        "candidate_counts": (candidate_summary.get("counts") if candidate_summary else {}),
        "candidate_due": (candidate_summary.get("due") if candidate_summary else []),
        "candidate_expired": (candidate_summary.get("expired") if candidate_summary else []),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"sources {result['sources']} active {active} provisional {len(provisional)} "
            f"overdue {len(overdue)} "
            f"watch {result['watch_entries']} ({result['watch_coverage']}) "
            f"candidates {result['candidates']} errors {len(errors)}"
        )
        for row in overdue:
            print(f"- overdue {row['id']} {row['review_due']} ({row['days_overdue']}d)")
        for row in result["candidate_expired"]:
            print(f"- expired candidate {row['id']} {row['expires_at']}")
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    return 1 if overdue or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
