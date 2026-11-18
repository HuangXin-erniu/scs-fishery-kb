#!/usr/bin/env python3
"""Validate the 150-row human review and compute the blind-pass gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from review_provenance import check_human, load, reviewer_kind

PASS = {"pass", "yes", "y", "1", "true", "通过"}
FAIL = {"fail", "no", "n", "0", "false", "不通过"}


def wilson(passes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = passes / total
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (centre - margin) / denom, (centre + margin) / denom


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-pass", type=float, default=0.90)
    parser.add_argument("--min-wilson", type=float, default=0.85)
    parser.add_argument("--provenance", default="")
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="treat a worksheet without provenance as legacy data (recorded, not human-verified)",
    )
    args = parser.parse_args(argv)
    rows = list(csv.DictReader(Path(args.csv).open(encoding="utf-8-sig")))
    provenance_path = (
        Path(args.provenance)
        if args.provenance
        else Path(args.csv).with_name("review-provenance.json")
    )
    provenance = load(provenance_path)
    if not provenance and rows and "reviewer_type" in rows[0]:
        provenance = {"reviewer_type": rows[0].get("reviewer_type", "")}
    human_ok, human_reason = check_human(provenance)
    if not provenance and args.allow_unverified:
        human_ok, human_reason = True, "unverified legacy worksheet (--allow-unverified)"
    verdicts = [str(row.get("human_verdict") or "").strip().lower() for row in rows]
    missing = [index + 2 for index, value in enumerate(verdicts) if not value]
    invalid = [
        index + 2 for index, value in enumerate(verdicts) if value and value not in PASS | FAIL
    ]
    judged = [value for value in verdicts if value in PASS | FAIL]
    passes = sum(1 for value in judged if value in PASS)
    rate = round(passes / len(judged), 4) if judged else 0.0
    low, high = wilson(passes, len(judged))
    complete = not missing and not invalid
    gate = complete and rate >= args.min_pass and low >= args.min_wilson and human_ok
    result = {
        "rows": len(rows),
        "judged": len(judged),
        "passes": passes,
        "rate": rate,
        "wilson_low": round(low, 4),
        "wilson_high": round(high, 4),
        "missing_rows": missing[:20],
        "missing_count": len(missing),
        "invalid_rows": invalid[:20],
        "complete": complete,
        "human_review_valid": human_ok,
        "provenance": {
            "path": str(provenance_path),
            "kind": reviewer_kind(provenance),
            "reason": human_reason,
        },
        "pass": gate,
        "thresholds": {"rate": args.min_pass, "wilson_low": args.min_wilson},
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
