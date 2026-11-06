#!/usr/bin/env python3
"""Validate playbooks, their fact references and their source ids."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scs_fkb.facts import DEFAULT_FACTS_DIR
from scs_fkb.knowledge_v2 import check_playbooks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playbooks", default="configs/playbooks")
    parser.add_argument("--facts", default=str(DEFAULT_FACTS_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_playbooks(
        Path(args.playbooks),
        facts_dir=Path(args.facts),
    )
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            f"playbooks {result.playbooks} approved {result.approved} "
            f"steps {result.steps} errors {len(result.errors)}"
        )
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
