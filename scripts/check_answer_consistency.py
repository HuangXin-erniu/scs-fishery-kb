#!/usr/bin/env python3
"""Reject an answer batch when different ids share the same answer body."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.audit.consistency import check  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    rows = [
        json.loads(line)
        for line in Path(args.answers).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    problems = check(rows)
    hard = [problem for problem in problems if problem[0] == "DUP_ANSWER"]
    payload = {
        "records": len(rows),
        "problems": problems,
        "dup_answer": [problem[1] for problem in hard],
        "pass": not hard,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for kind, ids, detail in problems:
        print(f"{kind} | {ids} | {detail}")
    print(f"{len(problems)} problems in {len(rows)} answers")
    return 0 if not hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
