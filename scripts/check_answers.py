#!/usr/bin/env python3
"""Validate canonical answers against the registered corpus."""

from __future__ import annotations

import argparse
import sys

from scs_fkb.knowledge_v2.answers import load_answers, validate_answers
from scs_fkb.registry import load_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", default="configs/knowledge/answers.yaml")
    args = parser.parse_args(argv)
    entries = load_answers(args.answers)
    errors = validate_answers(entries, registry=load_registry())
    approved = sum(1 for entry in entries if entry.get("status") == "approved")
    print(f"answers {len(entries)} approved {approved} errors {len(errors)}")
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
