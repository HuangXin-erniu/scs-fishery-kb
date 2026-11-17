#!/usr/bin/env python3
"""Compute the audit gate summary from a ledger; not an acceptance decision.

Human blind pass rate, expert signature and the published acceptance lines live
outside this file.  This script only makes the deterministic gate reproducible.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


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
    parser.add_argument("--answers", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--blind-pass", type=int, default=None)
    parser.add_argument("--blind-total", type=int, default=None)
    args = parser.parse_args(argv)
    records = [
        json.loads(line)
        for line in Path(args.answers).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counts: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    with Path(args.ledger).open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            counts[row.get("detector", "")] += 1
            severities[row.get("severity", "")] += 1
    cited = sum(1 for record in records if record.get("citations") and not record.get("abstained"))
    versioned = sum(
        1 for record in records if record.get("citations") and not record.get("abstained")
    )
    total = len(records)
    d7 = counts.get("D7", 0)
    d11 = counts.get("D11", 0)
    support_rate = round(1 - d7 / cited, 4) if cited else 0.0
    asof_rate = round(1 - d11 / versioned, 4) if versioned else 0.0
    blocking: list[str] = []
    for detector in ("D1", "D3", "D4", "D5"):
        if counts.get(detector, 0):
            blocking.append(f"{detector}={counts[detector]}")
    if severities.get("S1", 0):
        blocking.append(f"S1={severities['S1']}")
    if support_rate < 0.95:
        blocking.append(f"D7_support={support_rate}")
    if asof_rate < 0.95:
        blocking.append(f"asof={asof_rate}")
    wilson_low = None
    if args.blind_pass is not None and args.blind_total:
        low, high = wilson(args.blind_pass, args.blind_total)
        wilson_low = round(low, 4)
        rate = args.blind_pass / args.blind_total
        if rate < 0.90 or low < 0.85:
            blocking.append(f"blind={rate:.4f}/wilson_low={low:.4f}")
    result = {
        "scope": "deterministic audit gate; human blind and expert signature are separate",
        "records": total,
        "counts": dict(sorted(counts.items())),
        "severities": dict(sorted(severities.items())),
        "cited_records": cited,
        "d7_support_rate": support_rate,
        "asof_rate": asof_rate,
        "wilson_low": wilson_low,
        "blocking": blocking,
        "pass": not blocking,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
