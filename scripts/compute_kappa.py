#!/usr/bin/env python3
"""Cohen's kappa for the 30-row double annotation (human vs AI pre-label)."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    labels = sorted({label for pair in pairs for label in pair})
    observed = sum(1 for left, right in pairs if left == right) / len(pairs)
    expected = 0.0
    for label in labels:
        pa = sum(1 for left, _right in pairs if left == label) / len(pairs)
        pb = sum(1 for _left, right in pairs if right == label) / len(pairs)
        expected += pa * pb
    return 0.0 if expected == 1 else (observed - expected) / (1 - expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--human", default="human_verdict")
    parser.add_argument("--model", default="ai_label")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    pairs = []
    for row in csv.DictReader(Path(args.csv).open(encoding="utf-8-sig")):
        human = str(row.get(args.human) or "").strip().lower()
        model = str(row.get(args.model) or "").strip().lower()
        if human and model:
            pairs.append((human, model))
    value = round(kappa(pairs), 4)
    result = {
        "pairs": len(pairs),
        "kappa": value,
        "labels": dict(Counter(label for pair in pairs for label in pair)),
        "interpretation": "poor" if value < 0.6 else "acceptable",
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
