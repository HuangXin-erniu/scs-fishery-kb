from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .answer import answer_question
from .compare import run_comparison
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
from .dense import DenseError, DenseIndex, embeddings_dir, index_path
from .embed import DEFAULT_MODEL, FastEmbedEncoder
from .evaluate import title_tokens, write_report
from .ingest import IngestError, ingest, load_pipeline
from .jurisdiction import question_jurisdiction
from .lexicon import load_lexicon
from .models import Answer
from .parsers import ParseError, UnsupportedFormatError
from .reference import ReferenceError, diverse_hits
from .reference import lookup as reference_lookup
from .reference import lookup_term as reference_lookup_term
from .retrieve import Retriever
from .stats import StatsError
from .stats import query as stats_query
from .store import StoreError, load_chunks
from .watch import DEFAULT_WATCH, WatchError, run_watch
from .watch import write_report as write_watch_report
from .web import WebError, is_allowed, load_cards, load_web_sources, refresh


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


def _retriever(chunks, manifest, pipeline_path: str, lexicon=None, root=None) -> Retriever:
    pipeline = load_pipeline(Path(pipeline_path))
    retrieval = pipeline.get("retrieval") or {}
    mode = str(retrieval.get("mode", "bm25"))
    title_boost = float(retrieval.get("title_boost", 0.0))
    dense = encoder = None
    if mode != "bm25":
        if root is None:
            raise ValueError("dense and hybrid modes need a data root")
        version = str(manifest.get("index_version"))
        dense = DenseIndex.load(index_path(Path(root), DEFAULT_MODEL, version))
        encoder = FastEmbedEncoder(
            DEFAULT_MODEL, cache_dir=str(embeddings_dir(Path(root)) / "models")
        )
    return Retriever(
        chunks,
        titles=title_tokens(manifest.get("documents", [])),
        title_boost=title_boost,
        lexicon=lexicon,
        mode=mode,
        dense=dense,
        encoder=encoder,
        fusion_k=int(retrieval.get("fusion_k", 60)),
        bm25_weight=float(retrieval.get("bm25_weight", 1.0)),
        dense_weight=float(retrieval.get("dense_weight", 1.0)),
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
    retriever = _retriever(
        chunks, manifest, args.pipeline, _lexicon_for(args), root=_root(args.data_root)
    )
    hits = retriever.search(
        args.question,
        top_k=args.top_k,
        sensitivity_ceiling=args.sensitivity,
    )
    references = diverse_hits(reference_lookup(args.question, top_k=8, root=_root(args.data_root)))
    product_references = diverse_hits(
        reference_lookup(args.question, top_k=8, root=_root(args.data_root), collection="product")
    )
    policy_references = diverse_hits(
        reference_lookup(args.question, top_k=8, root=_root(args.data_root), collection="policy")
    )
    min_score, min_matched, _ = _pipeline_options(args.pipeline)
    if retriever.mode == "bm25":
        answer = answer_question(
            args.question,
            hits,
            min_score=min_score,
            min_matched=min_matched,
            extra_hits=policy_references,
        )
    elif retriever.gate_ok(args.question, min_score, min_matched):
        answer = answer_question(
            args.question,
            hits,
            min_score=0.0,
            min_matched=0,
            extra_hits=policy_references,
        )
    elif policy_references and question_jurisdiction(args.question):
        answer = answer_question(
            args.question,
            [],
            min_score=0.0,
            min_matched=0,
            extra_hits=policy_references,
        )
    else:
        answer = Answer(
            text="证据不足：检索到的证据覆盖不足，无法支持回答。",
            abstained=True,
            reason="weak_evidence",
        )
    statistics = []
    try:
        statistics = stats_query(args.question, root=_root(args.data_root))
    except StatsError:
        statistics = []
    if args.json:
        _print_json(
            {
                "question": args.question,
                "index_version": manifest.get("index_version"),
                "hits": [hit.to_dict() for hit in hits],
                "result": answer.to_dict(),
                "reference": [hit.to_dict() for hit in references],
                "product_reference": [hit.to_dict() for hit in product_references],
                "policy_reference": [hit.to_dict() for hit in policy_references],
                "statistics": [hit.to_dict() for hit in statistics],
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
    if product_references:
        print("product references:")
        for hit in product_references:
            snippet = " ".join(hit.chunk.text.split())[:200]
            print(f"  [{hit.chunk.doc_id}] {snippet}")
    if policy_references:
        print("policy references:")
        for hit in policy_references:
            snippet = " ".join(hit.chunk.text.split())[:200]
            print(f"  [{hit.chunk.doc_id}] {snippet}")
    if statistics:
        print("statistics:")
        for hit in statistics:
            print(f"  {hit.text} {hit.citation}")
            for note in hit.notes:
                print(f"    note: {note}")
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


def _embed(args: argparse.Namespace) -> int:
    root = _root(args.data_root)
    chunks, manifest = load_chunks(root)
    version = str(manifest.get("index_version"))
    path = index_path(root, args.model, version)
    if path.is_file() and not args.force:
        print(f"dense index already present for {version}: {path} (use --force to rebuild)")
        return 0
    cache = embeddings_dir(root) / "models"
    encoder = FastEmbedEncoder(args.model, cache_dir=str(cache))
    index = DenseIndex.build(chunks, encoder, version)
    info = index.save(path)
    if args.json:
        _print_json(
            {
                "model_id": info["model_id"],
                "count": info["count"],
                "dim": info["dim"],
                "sha256": info["sha256"],
            }
        )
    else:
        print(
            f"embedded {info['count']} chunks with {info['model_id']} "
            f"({info['dim']} dims) -> {info['sha256'][:16]}"
        )
    return 0


def _stats(args: argparse.Namespace) -> int:
    hits = stats_query(args.query, top_k=args.top_k, root=_root(args.data_root))
    if args.json:
        _print_json({"query": args.query, "hits": [hit.to_dict() for hit in hits]})
        return 0
    if not hits:
        print("no statistics row matched")
        return 0
    for hit in hits:
        print(f"{hit.text} {hit.citation}")
        for note in hit.notes:
            print(f"  note: {note}")
    return 0


def _watch(args: argparse.Namespace) -> int:
    report = run_watch(Path(args.config), offline=args.offline)
    if args.report:
        write_watch_report(report, Path(args.report))
    if args.json:
        _print_json(report)
        return 0
    for result in report["results"]:
        digest = (result.get("sha256") or "-")[:12]
        print(
            f"{result['id']:28} {result['status']:12} "
            f"http {result.get('http_status') or '-'} {digest}"
        )
    print(f"summary {report['summary']}")
    return 0


def _web_refresh(args: argparse.Namespace) -> int:
    sources = load_web_sources(Path(args.sources))
    cards = load_cards(Path(args.cards))
    if args.dry_run:
        rows = []
        for card in cards["cards"]:
            allowed, reason = is_allowed(str(card["url"]), sources["allowlist"])
            rows.append({"id": card["id"], "allowed": allowed, "reason": reason})
        if args.json:
            _print_json({"cards": rows})
        else:
            for row in rows:
                verdict = "allowed" if row["allowed"] else "blocked"
                print(f"{row['id']:24} {verdict:8} {row['reason']}")
        return 0 if all(row["allowed"] for row in rows) else 1
    cache = Path(args.cache_root).expanduser() if args.cache_root else data_root() / "web"
    report = refresh(Path(args.cards), Path(args.sources), cache, topic=args.topic)
    if args.json:
        _print_json(report)
    else:
        for row in report["cards"]:
            digest = (row.get("sha256") or "-")[:12]
            print(f"{row['id']:24} {row['status']:8} {digest} {row.get('error', '')}".rstrip())
        print(f"summary {{'ok': {report['ok']}, 'failed': {report['failed']}}}")
    return 0 if report["failed"] == 0 else 1


def _web_check(args: argparse.Namespace) -> int:
    sources = load_web_sources(Path(args.sources))
    allowed, reason = is_allowed(args.url, sources["allowlist"])
    if args.json:
        _print_json({"url": args.url, "allowed": allowed, "reason": reason})
    else:
        print(f"{'allowed' if allowed else 'blocked'}: {reason}")
    return 0 if allowed else 1


def _eval(args: argparse.Namespace) -> int:
    report = run_comparison(
        _root(args.data_root),
        Path(args.questions),
        Path(args.anchors),
        Path(args.pipeline),
        Path(args.lexicon),
    )
    if args.out:
        write_report(report, Path(args.out))
    if args.json:
        _print_json(report)
        return 0
    print(f"index {report['index_version']} model {report['model']}")
    for name, summary in report["arms"].items():
        extra = summary.get("p95_latency_ms")
        latency = f" p95 {extra} ms" if extra is not None else ""
        print(
            f"{name:14} recall {summary['recall_hits']}/{summary['answerable_questions']} "
            f"mrr {summary['mrr']:.2f} "
            f"abstain {summary['abstained_tests']}/{summary['abstention_tests']} "
            f"false {summary['false_refusals']} cite {summary['citation_resolution']:.2f}{latency}"
        )
    reference = report.get("reference_summary") or {}
    if reference:
        print(
            f"reference {reference.get('reference_hits', 0)}/"
            f"{reference.get('reference_questions', 0)}"
        )
    national = report.get("national_summary") or {}
    if national:
        print(
            f"national {national.get('national_hits', 0)}/{national.get('national_questions', 0)}"
        )
    jurisdiction = report.get("jurisdiction_summary") or {}
    if jurisdiction:
        print(
            f"jurisdiction {jurisdiction.get('jurisdiction_hits', 0)}/"
            f"{jurisdiction.get('jurisdiction_questions', 0)}"
        )
    statistics = report.get("statistics_summary") or {}
    if statistics:
        skipped = statistics.get("statistics_skipped", 0)
        note = f" ({skipped} skipped)" if skipped else ""
        print(
            f"statistics {statistics.get('statistics_hits', 0)}/"
            f"{statistics.get('statistics_questions', 0)}{note}"
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

    stats_parser = subparsers.add_parser("stats", help="query the local yearbook indicator table")
    stats_parser.add_argument("query")
    stats_parser.add_argument("--top-k", type=int, default=8)
    stats_parser.add_argument("--data-root", default=None)
    stats_parser.add_argument("--json", action="store_true")
    stats_parser.set_defaults(func=_stats)

    embed_parser = subparsers.add_parser("embed", help="build the local dense index")
    embed_parser.add_argument("--model", default=DEFAULT_MODEL)
    embed_parser.add_argument("--data-root", default=None)
    embed_parser.add_argument("--force", action="store_true")
    embed_parser.add_argument("--json", action="store_true")
    embed_parser.set_defaults(func=_embed)

    eval_parser = subparsers.add_parser("eval", help="evaluate retrieval, abstention and citations")
    eval_parser.add_argument("--questions", default=str(REPO_ROOT / "docs" / "questions.md"))
    eval_parser.add_argument("--anchors", default=str(DEFAULT_ANCHORS))
    eval_parser.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    eval_parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    eval_parser.add_argument("--data-root", default=None)
    eval_parser.add_argument("--out", default=None)
    eval_parser.add_argument("--json", action="store_true")
    eval_parser.set_defaults(func=_eval)

    watch_parser = subparsers.add_parser("watch", help="check the curated authoritative watch list")
    watch_parser.add_argument("--config", default=str(DEFAULT_WATCH))
    watch_parser.add_argument("--offline", action="store_true")
    watch_parser.add_argument("--report", default=None)
    watch_parser.add_argument("--json", action="store_true")
    watch_parser.set_defaults(func=_watch)

    web_parser = subparsers.add_parser("web", help="manage cached web cards")
    web_subparsers = web_parser.add_subparsers(dest="web_command", required=True)
    refresh_parser = web_subparsers.add_parser(
        "refresh", help="fetch allowlisted cards into the cache"
    )
    refresh_parser.add_argument("--cards", default=str(REPO_ROOT / "configs" / "web-cards.yaml"))
    refresh_parser.add_argument(
        "--sources", default=str(REPO_ROOT / "configs" / "web-sources.yaml")
    )
    refresh_parser.add_argument("--cache-root", default=None)
    refresh_parser.add_argument("--topic", default=None)
    refresh_parser.add_argument("--dry-run", action="store_true")
    refresh_parser.add_argument("--json", action="store_true")
    refresh_parser.set_defaults(func=_web_refresh)
    check_parser = web_subparsers.add_parser("check", help="check a URL against the allowlist")
    check_parser.add_argument("url")
    check_parser.add_argument("--sources", default=str(REPO_ROOT / "configs" / "web-sources.yaml"))
    check_parser.add_argument("--json", action="store_true")
    check_parser.set_defaults(func=_web_check)
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
        DenseError,
        StatsError,
        StoreError,
        WatchError,
        WebError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
