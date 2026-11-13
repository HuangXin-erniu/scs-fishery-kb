#!/usr/bin/env python3
"""Promote selected provisional sources to canonical in configs/corpus.yaml.

The script edits only the named entries and validates the resulting canonical
records. It never touches the index; rebuild with the normal commands afterwards.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.registry import validate_entry

DEFAULT_CORPUS = Path("configs/corpus.yaml")


def _block(text: str, source_id: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"(?ms)^- id: {re.escape(source_id)}\n.*?(?=^- id: |^gaps:|\Z)")
    match = pattern.search(text)
    return (match.start(), match.end()) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--reviewer", default="owner")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.corpus)
    text = path.read_text(encoding="utf-8")
    changed = 0
    for source_id in args.ids:
        span = _block(text, source_id)
        if span is None:
            raise SystemExit(f"source not found: {source_id}")
        old = text[span[0] : span[1]]
        loaded = yaml.safe_load(old)
        entry = loaded[0] if isinstance(loaded, list) and loaded else loaded
        if not isinstance(entry, dict) or entry.get("id") != source_id:
            raise SystemExit(f"unexpected block for {source_id}")
        ingest = dict(entry.get("ingest") or {})
        if ingest.get("tier") != "provisional":
            raise SystemExit(f"not provisional: {source_id}")
        ingest.update(
            {
                "tier": "canonical",
                "reviewed_by": args.reviewer,
                "reviewed_at": args.today,
                "review_note": f"human review confirmed {args.today}",
            }
        )
        entry["ingest"] = ingest
        currency = dict(entry.get("currency") or {})
        currency["note"] = "canonical practical source after human review"
        entry["currency"] = currency
        retrieval = dict(entry.get("retrieval") or {})
        retrieval["note"] = "canonical practical source; main index"
        entry["retrieval"] = retrieval
        errors = validate_entry(entry)
        if errors:
            raise SystemExit(f"{source_id}: {'; '.join(errors)}")
        lines = yaml.safe_dump(entry, allow_unicode=True, sort_keys=False).rstrip().splitlines()
        block = "- " + lines[0] + "\n" + "\n".join("  " + line for line in lines[1:]) + "\n"
        text = text[: span[0]] + block + text[span[1] :]
        changed += 1
    if args.dry_run:
        print(f"would promote {changed} sources")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"promoted {changed} sources in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
