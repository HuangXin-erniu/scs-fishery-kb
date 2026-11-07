#!/usr/bin/env python3
"""Run the private acceptance instrument and write a scored report.

Usage:
    SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... \
        PYTHONPATH=src python scripts/eval_accept.py [--split dev] [--limit 40]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_config(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _environment(data_root: Path) -> dict:
    manifest_path = data_root / "v2" / "index" / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    return {
        "data_root": str(data_root),
        "index_manifest": manifest if isinstance(manifest, dict) else {},
        "web": "off",
    }


def _build_llm(data_root: Path):
    from scs_fkb.llm import LLMConfig, LLMError
    from scs_fkb.rag import LLMCache, llm_answer_fn

    try:
        config = LLMConfig.from_env()
    except LLMError as exc:
        print(f"llm arm unavailable: {exc}", file=sys.stderr)
        return None, str(exc)
    cache = LLMCache(data_root / "llm-cache")
    from scs_fkb.llm import LLMClient

    return llm_answer_fn(LLMClient(config), cache), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT", ""))
    parser.add_argument("--task-id", default="P11-EVAL-159")
    parser.add_argument("--dataset-dir", default="")
    parser.add_argument("--config", default=str(ROOT / "configs" / "eval-accept.yaml"))
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="all")
    parser.add_argument("--dimension", default="")
    parser.add_argument("--persona", default="")
    parser.add_argument("--answerability", default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--llm", action="store_true", help="also run the optional LLM arm")
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="write the report and exit zero even when a pass line is missed",
    )
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        print("set --data-root and --run-root (or their environment variables)", file=sys.stderr)
        return 2

    from scs_fkb.eval_accept import (
        load_dataset,
        load_docmap,
        run_acceptance,
        select_rows,
    )
    from scs_fkb.eval_accept.points import ConceptSource, PointOverrides
    from scs_fkb.eval_accept.report import (
        metrics_payload,
        write_metrics,
        write_report,
        write_rows_csv,
    )
    from scs_fkb.eval_accept.scoring import (
        ScoringConfig,
        aggregate,
        gate_result,
        group_metrics,
        latency_summary,
        reason_clusters,
    )

    config = _load_config(Path(args.config))
    dataset_dir = Path(args.dataset_dir or Path(args.data_root) / "eval" / "acceptance")
    dataset_path = dataset_dir / "dataset.jsonl"
    manifest_path = dataset_dir / "manifest.json"
    try:
        dataset_manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        )
        rows = load_dataset(dataset_path)
        docmap = load_docmap(dataset_dir / "doc-map.yaml")
    except (OSError, ValueError) as exc:
        print(f"dataset error: {exc}", file=sys.stderr)
        return 2

    expected = (config.get("counts") or {}).get("questions")
    if expected and len(rows) != expected:
        print(f"dataset has {len(rows)} questions, config expects {expected}", file=sys.stderr)
        return 2

    concepts = ConceptSource.load(
        ROOT / "configs" / "terms.yaml",
        dataset_dir / "domain-terms.yaml",
    )
    overrides = PointOverrides.load(dataset_dir / "point-overrides.yaml")
    scoring = ScoringConfig.from_config(config)

    selected = select_rows(
        rows,
        split=None if args.split == "all" else args.split,
        dimension=args.dimension or None,
        persona=args.persona or None,
        answerability=args.answerability or None,
        limit=args.limit,
    )
    if not selected:
        print("no questions selected", file=sys.stderr)
        return 2

    from scs_fkb.service_v2 import build_service

    data_root = Path(args.data_root).expanduser()
    service = build_service(data_root=data_root, run_root=args.run_root)
    arm = "extractive"
    llm_fn = None
    llm_error = ""
    if args.llm:
        llm_fn, llm_error = _build_llm(data_root)
        arm = "llm" if llm_fn is not None else "extractive_after_llm_error"

    def progress(done: int, total: int) -> None:
        print(f"scored {done}/{total}", file=sys.stderr)

    scored = run_acceptance(
        selected,
        service,
        docmap=docmap,
        concepts=concepts,
        overrides=overrides,
        config=scoring,
        llm_fn=llm_fn,
        progress=progress,
    )
    overall = aggregate(scored)
    groups = group_metrics(scored)
    gate = gate_result(overall, scoring.thresholds)
    clusters = reason_clusters(scored)
    latency = latency_summary(scored)
    failures = sorted(
        (row for row in scored if row["band"] == 0.0 or row["flags"]),
        key=lambda row: (row["band"] if row["band"] is not None else 1.0, row["id"]),
    )[:40]

    out_dir = Path(args.run_root).expanduser() / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    write_rows_csv(scored, out_dir / "rows.csv")
    write_metrics(
        metrics_payload(
            dataset_manifest=dataset_manifest,
            docmap_summary=docmap.summary(),
            overall=overall,
            groups=groups,
            gate=gate,
            clusters=clusters,
            latency=latency,
            arm=arm,
            rows=len(scored),
            environment={**_environment(data_root), "llm_error": llm_error},
        ),
        out_dir / "metrics.json",
    )
    write_report(
        path=out_dir / "baseline.md",
        arm=arm,
        rows=len(scored),
        overall=overall,
        groups=groups,
        gate=gate,
        clusters=clusters,
        latency=latency,
        failures=failures,
    )
    print(
        f"arm={arm} questions={len(scored)} answered={overall['answered']} "
        f"point_coverage={overall['point_coverage']} citation={overall['citation_accuracy']} "
        f"misanswer={overall['misanswer_rate']} gate={'pass' if gate['passed'] else 'fail'}"
    )
    print(f"report: {out_dir / 'baseline.md'}")
    if gate["failures"]:
        for failure in gate["failures"]:
            print(f"gate: {failure}", file=sys.stderr)
    if not gate["passed"] and not args.allow_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
