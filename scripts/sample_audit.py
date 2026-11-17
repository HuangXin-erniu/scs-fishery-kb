#!/usr/bin/env python3
"""Stratified human sample: all S1, fixed themes, all gap_declared, Wilson/kappa."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

QUOTAS = {"休渔": 25, "证照": 25, "执法": 25, "生态": 20, "预报": 15, "补贴": 15, "其他": 25}


def wilson(passes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = passes / total
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (centre - margin) / denom, (centre + margin) / denom


def kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    labels = sorted({label for pair in pairs for label in pair})
    observed = sum(1 for a, b in pairs if a == b) / len(pairs)
    expected = 0.0
    for label in labels:
        pa = sum(1 for a, _b in pairs if a == label) / len(pairs)
        pb = sum(1 for _a, b in pairs if b == label) / len(pairs)
        expected += pa * pb
    return 0.0 if expected == 1 else (observed - expected) / (1 - expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20261117)
    args = parser.parse_args(argv)
    records = [
        json.loads(line)
        for line in Path(args.answers).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["id"]: row for row in records}
    s1 = defaultdict(set)
    with Path(args.ledger).open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("severity") == "S1":
                s1[row["id"]].add(row["detector"])
    selected: list[str] = []
    selected_set: set[str] = set()

    def add(ids: list[str]) -> None:
        for qid in ids:
            if qid in by_id and qid not in selected_set and len(selected) < args.limit:
                selected.append(qid)
                selected_set.add(qid)

    add(sorted(s1))
    gap = [
        row["id"]
        for row in records
        if row.get("gap_status") in {"refuse", "partial", "closed-no-public-source"}
    ]
    add(gap)
    rng = random.Random(args.seed)
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in records:
        if row["id"] not in selected_set:
            buckets[row.get("theme", "其他")].append(row["id"])
    for theme, quota in QUOTAS.items():
        ids = buckets.get(theme, [])
        rng.shuffle(ids)
        add(ids[:quota])
    remaining = [row["id"] for row in records if row["id"] not in selected_set]
    rng.shuffle(remaining)
    add(remaining[: max(0, args.limit - len(selected))])
    rows = []
    for qid in selected:
        row = by_id[qid]
        rows.append(
            {
                "id": qid,
                "source": row.get("source", ""),
                "theme": row.get("theme", ""),
                "question": row.get("question", ""),
                "visible_answer": row.get("visible_answer", ""),
                "trace_ref": row.get("trace_ref", ""),
                "s1_flags": ";".join(sorted(s1.get(qid, set()))),
                "human_verdict": "",
                "citation_ok": "",
                "conclusion_ok": "",
                "refusal_ok": "",
                "asof_ok": "",
                "note": "",
            }
        )
    with Path(args.out).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"records={len(records)} s1={len(s1)} selected={len(rows)}")
    print(f"wilson_150_pass7={wilson(143, 150)} kappa_placeholder={kappa([])}")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
