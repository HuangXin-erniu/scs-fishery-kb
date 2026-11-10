#!/usr/bin/env python3
"""Read-only watch run over the curated authoritative pages.

A live run fetches each page, compares the body hash with the recorded baseline
and writes a report. It never edits the registry, never ingests a page and never
promotes a candidate; ``--propose`` only writes candidate drafts under the run
root for a human to review.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.candidates import load_candidates, propose_from_watch
from scs_fkb.config import REPO_ROOT
from scs_fkb.watch import (
    DEFAULT_WATCH,
    WatchError,
    load_baseline,
    run_watch,
    save_baseline,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_WATCH))
    parser.add_argument("--offline", action="store_true", help="replay recorded statuses")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="record the hashes observed by this live run under the data root",
    )
    parser.add_argument(
        "--propose",
        action="store_true",
        help="write candidate drafts for changed or unbaselined pages under the run root",
    )
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--task-id", default="P17-LOOP-209")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.baseline and args.offline:
        print("error: --baseline needs a live run", file=sys.stderr)
        return 2
    if not args.run_root:
        print("error: set SCS_FKB_RUN_ROOT or pass --run-root", file=sys.stderr)
        return 2

    baseline_path = None
    if args.data_root:
        baseline_path = Path(args.data_root).expanduser() / "watch" / "baseline.json"
    try:
        report = run_watch(
            Path(args.config),
            offline=args.offline,
            baseline_path=baseline_path,
        )
    except WatchError as exc:
        print(f"watch error: {exc}", file=sys.stderr)
        return 2

    if args.baseline and baseline_path is not None:
        report["baseline_written"] = save_baseline(report, baseline_path)
        report["baseline"] = str(baseline_path)
    elif baseline_path is not None:
        report["baseline"] = str(baseline_path) if load_baseline(baseline_path) else None

    proposals: list[dict] = []
    if args.propose:
        candidates_path = REPO_ROOT / "configs" / "candidates.yaml"
        existing = load_candidates(candidates_path) if candidates_path.is_file() else []
        proposals = propose_from_watch(report, existing)
        report["proposals"] = proposals

    report_dir = Path(args.run_root).expanduser() / args.task_id
    report_path = report_dir / f"watch-{args.today}.json"
    write_report(report, report_path)
    if proposals:
        proposal_path = report_dir / "candidates-proposed.yaml"
        proposal_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "updated_at": args.today,
                    "candidates": proposals,
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        report["proposal_path"] = str(proposal_path)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
    else:
        for result in report["results"]:
            digest = (result.get("sha256") or "-")[:12]
            print(
                f"{result['id']:34} {result['status']:12} "
                f"http {result.get('http_status') or '-':>3} {digest}"
            )
        print(f"summary {report['summary']}")
        print(f"report {report_path}")
        for proposal in proposals:
            print(f"proposal {proposal['id']} {proposal['watch_ref']} {proposal['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
