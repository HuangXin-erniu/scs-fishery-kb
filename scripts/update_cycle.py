#!/usr/bin/env python3
"""Run one semi-automatic update cycle.

Default is offline: it replays the recorded watch statuses, compares them with
the candidate queue and writes a dated report/plan under the run root. Nothing
is registered, ingested or indexed. `--live` opens the network and is an
explicit operator action.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from scs_fkb.update import run_cycle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--live", action="store_true", help="open the network (operator action)")
    parser.add_argument("--watch-json", default="", help="replay a recorded watch report")
    parser.add_argument("--registry", default="configs/corpus.yaml")
    parser.add_argument("--candidates", default="configs/candidates.yaml")
    parser.add_argument("--watch-config", default="configs/source-watch.yaml")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.run_root:
        print("error: set SCS_FKB_RUN_ROOT or pass --run-root", file=sys.stderr)
        return 2
    try:
        today = date.fromisoformat(args.today)
    except ValueError:
        print(f"error: invalid --today {args.today}", file=sys.stderr)
        return 2
    watch_report = None
    if args.watch_json:
        path = Path(args.watch_json).expanduser()
        watch_report = json.loads(path.read_text(encoding="utf-8"))
    summary = run_cycle(
        data_root=args.data_root,
        run_root=args.run_root,
        today=today,
        registry_path=args.registry,
        candidates_path=args.candidates,
        watch_config=args.watch_config,
        watch_report=watch_report,
        live=args.live,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"update {summary['today']} mode={summary['mode']} "
            f"changes={summary['changes']} matched={summary['matched']} "
            f"provisional={len(summary['plans'])} rejected={len(summary['rejected'])}"
        )
        print(f"report: {summary['report']}")
        for row in summary["rejected"]:
            print(f"- {row['stage']}: {row.get('candidate_id') or row['watch_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
