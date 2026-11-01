from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .answer import answer_question
from .config import (
    DEFAULT_ANCHORS,
    DEFAULT_CONFIG,
    DEFAULT_LEXICON,
    DEFAULT_PIPELINE,
    REPO_ROOT,
    ConfigError,
    data_root,
    sensitivity_ceiling,
)
from .corpus import CorpusError
from .evaluate import evaluate, title_tokens, write_report
from .ingest import IngestError, ingest, load_pipeline
from .lexicon import load_lexicon
from .parsers import ParseError, UnsupportedFormatError
from .reference import ReferenceError
from .reference import lookup as reference_lookup
from .reference import lookup_term as reference_lookup_term
from .retrieve import Retriever
from .store import StoreError, load_chunks


def _root(value: str | None) -> Path:
    return Path(value).expanduser() if value else data_root()


def _pipeline_options(pipeline_path: str) -> tuple[float, int, float]:
    pipeline = load_pipeline(Path(pipeline_path))
    answer_config = pipeline.get("answer") or {}
    retrieval_config = pipeline.get("retrieval") or {}
    return (
        float(answer_config.get("min_score", 0.0)),
        int(answer_config.get("min_matched", 3)),
        float(retrieval_config.get("title_boost", 0.0)),
    )


def _lexicon_for(args: argparse.Namespace) -> list[dict[str, object]]:
    pipeline = load_pipeline(Path(args.pipeline))
    retrieval_config = pipeline.get("retrieval") or {}
    if not retrieval_config.get("lexicon_expand", False):
        return []
    return load_lexicon(Path(args.lexicon))


def _retriever(chunks, manifest, pipeline_path: str, lexicon=None) -> Retriever:
    _, _, title_boost = _pipeline_options(pipeline_path)
    return Retriever(
        chunks,
        titles=title_tokens(manifest.get("documents", [])),
        title_boost=title_boost,
        lexicon=lexicon,
    )


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
    hits = _retriever(chunks, manifest, args.pipeline, _lexicon_for(args)).search(
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
    hits = _retriever(chunks, manifest, args.pipeline, _lexicon_for(args)).search(
        args.question,
        top_k=args.top_k,
        sensitivity_ceiling=args.sensitivity,
    )
    references = reference_lookup(args.question, root=_root(args.data_root))
    min_score, min_matched, _ = _pipeline_options(args.pipeline)
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
                "reference": [hit.to_dict() for hit in references],
            }
        )
        return 0
    if answer.abstained:
        print(f"ABSTAIN ({answer.reason}): {answer.text}")
    else:
        print(answer.text)
    if references:
        print("standard definition references:")
        for hit in references:
            snippet = " ".join(hit.chunk.text.split())[:200]
            print(f"  [{hit.chunk.doc_id}] {snippet}")
    return 0


def _define(args: argparse.Namespace) -> int:
    hits = reference_lookup_term(args.term, top_k=args.top_k, root=_root(args.data_root))
    if args.json:
        _print_json({"term": args.term, "reference": [hit.to_dict() for hit in hits]})
        return 0
    if not hits:
        print(f"no CWP concept matched: {args.term}")
        return 0
    for rank, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.chunk.text.split())[:300]
        print(f"[{rank}] {hit.chunk.doc_id} score={hit.score:.2f}")
        print(f"    {snippet}")
    return 0


def _eval(args: argparse.Namespace) -> int:
    pipeline = load_pipeline(Path(args.pipeline))
    answer_config = pipeline.get("answer") or {}
    retrieval_config = pipeline.get("retrieval") or {}
    report = evaluate(
        Path(args.questions),
        Path(args.anchors),
        _root(args.data_root),
        min_score=float(answer_config.get("min_score", 0.0)),
        min_matched=int(answer_config.get("min_matched", 3)),
        top_k=int(retrieval_config.get("top_k", 5)),
        title_boost=float(retrieval_config.get("title_boost", 0.0)),
        lexicon=load_lexicon(Path(args.lexicon))
        if retrieval_config.get("lexicon_expand", False)
        else [],
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
        f"reference {summary['reference_hits']}/{summary['reference_questions']}; "
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
    retrieve_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    retrieve_parser.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    retrieve_parser.add_argument("--sensitivity", default=sensitivity_ceiling())
    retrieve_parser.add_argument("--data-root", default=None)
    retrieve_parser.add_argument("--json", action="store_true")
    retrieve_parser.set_defaults(func=_retrieve)

    ask_parser = subparsers.add_parser("ask", help="answer with extracted evidence citations")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    ask_parser.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ask_parser.add_argument("--sensitivity", default=sensitivity_ceiling())
    ask_parser.add_argument("--data-root", default=None)
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.set_defaults(func=_ask)

    define_parser = subparsers.add_parser(
        "define", help="look up a CWP definition for a Chinese term"
    )
    define_parser.add_argument("term")
    define_parser.add_argument("--top-k", type=int, default=3)
    define_parser.add_argument("--data-root", default=None)
    define_parser.add_argument("--json", action="store_true")
    define_parser.set_defaults(func=_define)

    eval_parser = subparsers.add_parser("eval", help="evaluate retrieval, abstention and citations")
    eval_parser.add_argument("--questions", default=str(REPO_ROOT / "docs" / "questions.md"))
    eval_parser.add_argument("--anchors", default=str(DEFAULT_ANCHORS))
    eval_parser.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
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
        ReferenceError,
        StoreError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
