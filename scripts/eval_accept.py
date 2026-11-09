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


def _answer_lengths(scored: list[dict]) -> dict:
    """Answer-size distribution, recorded next to the metrics for window sweeps."""
    values = sorted(len(str(row.get("answer") or "")) for row in scored if not row.get("abstained"))
    if not values:
        return {"answered": 0}
    count = len(values)
    return {
        "answered": count,
        "min": values[0],
        "mean": round(sum(values) / count, 1),
        "p50": values[count // 2],
        "p95": values[min(count - 1, int(round(0.95 * (count - 1))))],
        "max": values[-1],
    }


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


def _build_llm(data_root: Path, arm: str = "single"):
    from scs_fkb.answer_v3 import ChannelBook, compose
    from scs_fkb.answer_v3.llm_answer import answer_with_llm
    from scs_fkb.llm import LLMClient, LLMConfig, LLMError
    from scs_fkb.models import Answer
    from scs_fkb.rag import LLMCache
    from scs_fkb.registry import load_registry
    from scs_fkb.retrieve_v2 import build_retriever

    try:
        config = LLMConfig.from_env()
    except LLMError as exc:
        print(f"llm arm unavailable: {exc}", file=sys.stderr)
        return None, str(exc)
    client = LLMClient(config)
    cache = LLMCache(data_root / "llm-cache")
    retriever = build_retriever(data_root, reranker=False)
    registry = load_registry()
    channels = ChannelBook.load()

    from scs_fkb.answer import answer_question

    def single_answer(question: str, hits: list) -> Answer:
        try:
            answer = answer_with_llm(question, hits, client, cache)
        except LLMError:
            answer = None
        if answer is None or answer.abstained:
            fallback = answer_question(
                question,
                hits,
                min_score=0.0,
                min_matched=0,
                require_corpus=True,
            )
            if not fallback.abstained:
                answer = fallback
            elif answer is None:
                return fallback
        return answer

    if arm == "dump":
        from scs_fkb.answer_v3.dump_arm import answer_with_dump
        from scs_fkb.retrieve_v2.rewrite import rewrite

        def dump_arm(question: str, _hits: list) -> Answer:
            rewrites = rewrite(question, client, cache)
            answer = answer_with_dump(question, retriever, queries=rewrites)
            if answer.abstained:
                return answer
            contract = compose(
                question,
                answer.text,
                doc_ids=[item.doc_id for item in answer.citations],
                registry=registry,
                channels=channels,
            )
            if contract.answerability == "abstain":
                return Answer(
                    text=contract.body, citations=[], abstained=True, reason="gap_declared"
                )
            return Answer(
                text=contract.body,
                citations=answer.citations,
                abstained=False,
                reason="dump_compose",
            )

        return dump_arm, ""

    if arm == "quotes":
        from scs_fkb.answer_v3.quotes_arm import answer_with_quotes

        def quotes_arm(question: str, _hits: list) -> Answer:
            base_hits = retriever.search_queries([question], top_k=8)
            base = single_answer(question, base_hits)

            def fallback() -> Answer:
                return base

            answer = answer_with_quotes(question, retriever, client, cache, fallback=fallback)
            if answer.abstained:
                return answer
            contract = compose(
                question,
                answer.text,
                doc_ids=[item.doc_id for item in answer.citations],
                registry=registry,
                channels=channels,
            )
            if contract.answerability == "abstain":
                return Answer(
                    text=contract.body, citations=[], abstained=True, reason="gap_declared"
                )
            return Answer(
                text=contract.body,
                citations=answer.citations,
                abstained=False,
                reason="quotes_compose",
            )

        return quotes_arm, ""

    if arm == "facet":
        from scs_fkb.answer_v3.facet_arm import answer_with_facets

        def facet_arm(question: str, _hits: list) -> Answer:
            base_hits = retriever.search_queries([question], top_k=8)
            base = single_answer(question, base_hits)

            def fallback() -> Answer:
                return base

            answer = answer_with_facets(
                question,
                retriever,
                client,
                cache,
                fallback=fallback,
                base_answer=base,
                base_hits=base_hits,
            )
            if answer.abstained:
                return answer
            contract = compose(
                question,
                answer.text,
                doc_ids=[item.doc_id for item in answer.citations],
                registry=registry,
                channels=channels,
            )
            if contract.answerability == "abstain":
                return Answer(
                    text=contract.body, citations=[], abstained=True, reason="gap_declared"
                )
            return Answer(
                text=contract.body,
                citations=answer.citations,
                abstained=False,
                reason="facet_compose",
            )

        return facet_arm, ""

    def arm(question: str, _hits: list) -> Answer:
        evidence = retriever.search(question, top_k=8)
        answer = single_answer(question, evidence)
        if answer.abstained:
            return answer
        contract = compose(
            question,
            answer.text,
            doc_ids=[item.doc_id for item in answer.citations],
            registry=registry,
            channels=channels,
        )
        if contract.answerability == "abstain":
            return Answer(
                text=contract.body,
                citations=[],
                abstained=True,
                reason="gap_declared",
            )
        return Answer(
            text=contract.body,
            citations=answer.citations,
            abstained=False,
            reason="llm_compose",
        )

    return arm, ""


def _run_llm_rows(
    rows,
    service,
    llm_fn,
    *,
    workers: int,
    docmap,
    concepts,
    overrides,
    config,
    progress,
):
    """Run the network-bound arm concurrently; retrieval and scoring stay in order."""
    from concurrent.futures import ThreadPoolExecutor

    from scs_fkb.eval_accept.runner import query_service
    from scs_fkb.eval_accept.scoring import score_row

    retriever = getattr(service, "retriever", None)
    prepared = []
    for row in rows:
        hits = retriever.search(str(row.get("question") or ""), top_k=8) if retriever else []
        prepared.append((row, hits))

    def call(item):
        row, hits = item
        try:
            return (
                row["id"],
                query_service(
                    service, str(row.get("question") or ""), llm_fn=lambda q, _h: llm_fn(q, hits)
                ),
                "",
            )
        except Exception as exc:  # noqa: BLE001 - a failing question is data
            return (
                row["id"],
                {
                    "answer": "",
                    "citations": [],
                    "abstained": True,
                    "reason": "runner_error",
                    "mode": "error",
                    "latency_ms": 0,
                },
                f"{type(exc).__name__}: {exc}",
            )

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for row_id, result, error in pool.map(call, prepared):
            results[row_id] = (result, error)
            done += 1
            if progress is not None and done % 25 == 0:
                progress(done, len(rows))

    scored = []
    for row in rows:
        result, error = results[row["id"]]
        scored_row = score_row(
            row,
            result,
            docmap=docmap,
            concepts=concepts,
            overrides=overrides,
            config=config,
        )
        scored_row["question"] = row.get("question")
        scored_row["error"] = error
        scored.append(scored_row)
    return scored


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
        "--llm-arm",
        choices=["single", "facet", "quotes", "dump"],
        default="single",
        help="LLM arm variant: single-pass or facet answering",
    )
    parser.add_argument(
        "--llm-workers",
        type=int,
        default=1,
        help="concurrent LLM calls (retrieval stays sequential)",
    )
    parser.add_argument(
        "--llm-answerability",
        default="",
        help=(
            "comma-separated answerability labels that use the LLM arm (others stay deterministic)"
        ),
    )
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
        llm_fn, llm_error = _build_llm(data_root, args.llm_arm)
        arm = (
            (
                "facet"
                if args.llm_arm == "facet"
                else ("quotes" if args.llm_arm == "quotes" else "llm")
            )
            if llm_fn is not None
            else "extractive_after_llm_error"
        )

    def progress(done: int, total: int) -> None:
        print(f"scored {done}/{total}", file=sys.stderr)

    scope = {item.strip() for item in args.llm_answerability.split(",") if item.strip()}
    if llm_fn is not None and scope:
        llm_rows = [row for row in selected if row.get("answerability") in scope]
        deterministic_rows = [row for row in selected if row.get("answerability") not in scope]
        scored = []
        if llm_rows:
            if args.llm_workers > 1:
                scored.extend(
                    _run_llm_rows(
                        llm_rows,
                        service,
                        llm_fn,
                        workers=args.llm_workers,
                        docmap=docmap,
                        concepts=concepts,
                        overrides=overrides,
                        config=scoring,
                        progress=progress,
                    )
                )
            else:
                scored.extend(
                    run_acceptance(
                        llm_rows,
                        service,
                        docmap=docmap,
                        concepts=concepts,
                        overrides=overrides,
                        config=scoring,
                        llm_fn=llm_fn,
                        progress=progress,
                    )
                )
        if deterministic_rows:
            scored.extend(
                run_acceptance(
                    deterministic_rows,
                    service,
                    docmap=docmap,
                    concepts=concepts,
                    overrides=overrides,
                    config=scoring,
                    llm_fn=None,
                    progress=progress,
                )
            )
    else:
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
    lengths = _answer_lengths(scored)
    (out_dir / "answer_lengths.json").write_text(
        json.dumps(lengths, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"arm={arm} questions={len(scored)} answered={overall['answered']} "
        f"point_coverage={overall['point_coverage']} citation={overall['citation_accuracy']} "
        f"misanswer={overall['misanswer_rate']} gate={'pass' if gate['passed'] else 'fail'} "
        f"answer_chars_mean={lengths.get('mean')}"
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
