#!/usr/bin/env python3
"""Run the 120-question v2 evaluation and enforce the regression gate."""

from __future__ import annotations

import argparse
import json
import os
import sys

from scs_fkb.eval_v2 import run_eval, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--questions", default="configs/eval-v2.yaml")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        raise SystemExit("set SCS_FKB_DATA_ROOT and SCS_FKB_RUN_ROOT")
    from scs_fkb.service_v2 import build_service

    service = build_service(data_root=args.data_root, run_root=args.run_root)
    result = run_eval(
        service,
        questions_path=args.questions,
        split=args.split,
        limit=args.limit,
    )
    metrics_path, report_path = write_report(result, args.run_root)
    print(
        json.dumps({"passed": result["passed"], "failures": result["failures"]}, ensure_ascii=False)
    )
    print(f"metrics: {metrics_path}")
    print(f"report: {report_path}")
    if args.write_baseline:
        baseline = metrics_path.with_name("baseline.json")
        baseline.write_text(
            json.dumps(result["groups"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"baseline: {baseline}")
    if not result["passed"]:
        for failure in result["failures"]:
            print(f"GATE FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
