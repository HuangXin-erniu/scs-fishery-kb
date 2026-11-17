#!/usr/bin/env python3
"""Summarise the defect ledger into a first-round audit report."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    rows = list(csv.DictReader(Path(args.ledger).open(encoding="utf-8-sig")))
    by_detector = Counter(row["detector"] for row in rows)
    by_severity = Counter(row["severity"] for row in rows)
    by_stage = Counter(row["stage"] for row in rows)
    lines = [
        "# Audit baseline",
        "",
        f"- findings: {len(rows)}",
        f"- by detector: {dict(sorted(by_detector.items()))}",
        f"- by severity: {dict(sorted(by_severity.items()))}",
        f"- by stage: {dict(sorted(by_stage.items()))}",
        "",
        "## Gate-relevant counts",
        "",
        f"- S1: {by_severity.get('S1', 0)}",
        f"- D1: {by_detector.get('D1', 0)}",
        f"- D3: {by_detector.get('D3', 0)}",
        f"- D4: {by_detector.get('D4', 0)}",
        f"- D5: {by_detector.get('D5', 0)}",
        f"- D7: {by_detector.get('D7', 0)}",
        "",
        "This is a defect ledger, not an acceptance decision.",
    ]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
