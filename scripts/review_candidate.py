#!/usr/bin/env python3
"""Build a review package for one practical-source candidate (no network)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from scs_fkb.candidates import load_candidates
from scs_fkb.update.review import review_candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--candidates", default="configs/candidates.yaml")
    parser.add_argument("--text-chars", type=int, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--license", dest="license_value", required=True)
    parser.add_argument("--sensitivity", required=True)
    parser.add_argument("--practical-domain", default="other")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    candidates = load_candidates(args.candidates)
    candidate = next((item for item in candidates if item.get("id") == args.candidate_id), None)
    if candidate is None:
        print(f"error: candidate not found: {args.candidate_id}", file=sys.stderr)
        return 2
    package = review_candidate(
        candidate,
        text_chars=args.text_chars,
        sha256=args.sha256,
        license_value=args.license_value,
        sensitivity=args.sensitivity,
        practical_domain=args.practical_domain,
        today=date.fromisoformat(args.today),
    )
    payload = package.to_dict()
    if args.write:
        if not args.run_root:
            print("error: --write needs SCS_FKB_RUN_ROOT or --run-root", file=sys.stderr)
            return 2
        directory = Path(args.run_root).expanduser().resolve() / "candidates" / args.candidate_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "review.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (directory / "review.md").write_text(
            "\n".join(
                [
                    f"# Candidate review {args.candidate_id}",
                    "",
                    f"- Acceptable: `{payload['acceptable']}`",
                    f"- Quality: {json.dumps(payload['quality'], ensure_ascii=False)}",
                    f"- Actions: {', '.join(payload['actions'])}",
                    "",
                    "The entry is provisional; a human still decides canonical promotion.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"package: {directory}")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"candidate={package.candidate_id} acceptable={package.acceptable} "
            f"reasons={list(package.quality.reasons)}"
        )
    return 0 if package.acceptable else 1


if __name__ == "__main__":
    raise SystemExit(main())
