#!/usr/bin/env python3
"""Merge product-path audit artifacts, dedupe by id and add inline citations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.audit.merge import merge_artifacts, write_jsonl  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, help="dataset JSONL with ids")
    parser.add_argument("--answers", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    rows = merge_artifacts(Path(args.questions), [Path(path) for path in args.answers])
    out = Path(args.out)
    write_jsonl(out, rows)
    questions = len(
        [
            line
            for line in Path(args.questions).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    )
    missing = questions - len(rows)
    print(f"questions={questions} merged={len(rows)} missing={missing} -> {out}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
