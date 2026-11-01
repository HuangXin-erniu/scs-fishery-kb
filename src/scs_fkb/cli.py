from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .answer import answer_question
from .config import (
    DEFAULT_CONFIG,
    DEFAULT_PIPELINE,
    REPO_ROOT,
    ConfigError,
    data_root,
    sensitivity_ceiling,
)
from .corpus import CorpusError
from .evaluate import evaluate, write_report
from .ingest import IngestError, ingest, load_pipeline
from .parsers import ParseError, UnsupportedFormatError
from .retrieve import Retriever
from .store import StoreError, load_chunks


def _root(value: str | None) -> Path:
    return Path(value).expanduser() if value else data_root()


def _answer_thresholds(pipeline_path: str) -> tuple[float, int]:
    pipeline = load_pipeline(Path(pipeline_path))
    answer_config = pipeline.get("answer") or {}
    return float(answer_config.get("min_score", 0.0)), int(answer_config.get("min_matched", 3))


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _ingest(args: argparse.Namespace) -> int:
    summary = ingest(Path(args.config), Path(args.pipeline), _root(args.data_root))
    if args.json:
        _print_json(summary)
    else:
        print(
            f"ingested {summary['documents']} documents, "
            f"{summary['chunks']} chunks, index {summary['index_version']}"
        )
        for source_id, count in summary["counts"].items():
            print(f"  {source_id}: {count} chunks")
    return 0


def _retrieve(args: argparse.Namespace) -> int:
    chunks, manifest = load_chunks(_root(args.data_root))
    hits = Retriever(chunks).search(
        args.query,
        top_k=args.top_k,
        sensitivity_ceiling=args.sensitivity,
    )
    if args.json:
        _print_json(
            {
                "query": args.query,
                "index_version": manifest.get("index_version"),
                "hits": [hit.to_dict() for hit in hits],
            }
        )
        return 0
    if not hits:
        print("no results")
        return 0
    for rank, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.chunk.text.split())[:160]
        print(
            f"[{rank}] score={hit.score:.3f} "
            f"{hit.chunk.doc_id} p.{hit.chunk.page} §{hit.chunk.section}"
        )
        print(f"    {snippet}")
    return 0


def _ask(args: argparse.Namespace) -> int:
    chunks, manifest = load_chunks(_root(args.data_root))
    hits = Retriever(chunks).search(
        args.question,
        top_k=args.top_k,
        sensitivity_ceiling=args.sensitivity,
    )
    min_score, min_matched = _answer_thresholds(args.pipeline)
    answer = answer_question(
        args.question,
        hits,
        min_score=min_score,
        min_matched=min_matched,
    )
    if args.json:
        _print_json(
            {
                "question": args.question,
                "index_version": manifest.get("index_version"),
                "hits": [hit.to_dict() for hit in hits],
                "result": answer.to_dict(),
            }
        )
        return 0
    if answer.abstained:
        print(f"ABSTAIN ({answer.reason}): {answer.text}")
        return 0
    print(answer.text)
    return 0


def _eval(args: argparse.Namespace) -> int:
    pipeline = load_pipeline(Path(args.pipeline))
    answer_config = pipeline.get("answer") or {}
    retrieval_config = pipeline.get("retrieval") or {}
    report = evaluate(
        Path(args.questions),
        _root(args.data_root),
        pipeline["documents"],
        min_score=float(answer_config.get("min_score", 0.0)),
        min_matched=int(answer_config.get("min_matched", 3)),
        top_k=int(retrieval_config.get("top_k", 5)),
    )
    if args.out:
        write_report(report, Path(args.out))
    if args.json:
        _print_json(report)
        return 0
    summary = report["summary"]
    print(
        f"recall@5 {summary['recall_hits']}/{summary['answerable_questions']} "
        f"({summary['recall_at_5']:.2f}); "
        f"abstention {summary['abstained_tests']}/{summary['abstention_tests']}; "
        f"false refusals {summary['false_refusals']}; "
        f"citation resolution {summary['citation_resolution']:.2f}; "
        f"index {report['index_version']}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scs-fkb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="parse the configured sources and build chunks"
    )
    ingest_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    ingest_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    ingest_parser.add_argument("--data-root", default=None)
    ingest_parser.add_argument("--json", action="store_true")
    ingest_parser.set_defaults(func=_ingest)

    retrieve_parser = subparsers.add_parser("retrieve", help="retrieve ranked evidence")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--top-k", type=int, default=5)
    retrieve_parser.add_argument("--sensitivity", default=sensitivity_ceiling())
    retrieve_parser.add_argument("--data-root", default=None)
    retrieve_parser.add_argument("--json", action="store_true")
    retrieve_parser.set_defaults(func=_retrieve)

    ask_parser = subparsers.add_parser("ask", help="answer with extracted evidence citations")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    ask_parser.add_argument("--sensitivity", default=sensitivity_ceiling())
    ask_parser.add_argument("--data-root", default=None)
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.set_defaults(func=_ask)

    eval_parser = subparsers.add_parser("eval", help="evaluate retrieval, abstention and citations")
    eval_parser.add_argument("--questions", default=str(REPO_ROOT / "docs" / "questions.md"))
    eval_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    eval_parser.add_argument("--data-root", default=None)
    eval_parser.add_argument("--out", default=None)
    eval_parser.add_argument("--json", action="store_true")
    eval_parser.set_defaults(func=_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (
        ConfigError,
        CorpusError,
        IngestError,
        ParseError,
        UnsupportedFormatError,
        StoreError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
