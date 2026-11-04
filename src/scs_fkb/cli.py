from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from .answer import answer_question, augment_with_external
from .candidates import (
    DEFAULT_CANDIDATES,
    CandidateError,
    check_candidates,
    load_candidates,
    propose_from_watch,
)
from .claims import classify, load_claims, record_gap, summarize_gaps
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
from .coverage import coverage_report
from .dense import DenseError, DenseIndex, embeddings_dir, index_path
from .embed import DEFAULT_MODEL, FastEmbedEncoder
from .evaluate import load_anchors, summarize, title_tokens, write_report
from .ingest import IngestError, ingest, load_pipeline
from .jurisdiction import question_jurisdiction
from .knowledge import KnowledgeError, list_notes
from .knowledge import approve as approve_note
from .knowledge import check as check_knowledge
from .lexicon import load_lexicon
from .llm import LLMClient, LLMConfig, LLMError
from .models import Answer
from .parsers import ParseError, UnsupportedFormatError
from .rag import SCORE_PROMPT_VERSION, LLMCache, llm_answer_fn, score_answer
from .reference import ReferenceError, diverse_hits
from .reference import lookup as reference_lookup
from .reference import lookup_term as reference_lookup_term
from .registry import RegistryError, check_currency, load_registry
from .retrieve import Retriever
from .stats import StatsError
from .stats import query as stats_query
from .store import StoreError, load_chunks
from .watch import DEFAULT_WATCH, WatchError, due_report, run_watch
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
    summary = ingest(
        Path(args.config),
        Path(args.pipeline),
        _root(args.data_root),
        knowledge_dir=Path(args.knowledge_dir) if args.knowledge_dir else None,
        include_web=not args.no_web,
        include_knowledge=not args.no_knowledge,
        external_only=args.external_only,
    )
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
    hits = _retriever(
        chunks, manifest, args.pipeline, _lexicon_for(args), root=_root(args.data_root)
    ).search(
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
    try:
        product_references = diverse_hits(
            reference_lookup(
                args.question, top_k=8, root=_root(args.data_root), collection="product"
            )
        )
    except (ReferenceError, KeyError):
        product_references = []
    policy_references = diverse_hits(
        reference_lookup(args.question, top_k=8, root=_root(args.data_root), collection="policy")
    )
    min_score, min_matched, _ = _pipeline_options(args.pipeline)
    require_corpus = bool(
        (load_pipeline(Path(args.pipeline)).get("answer") or {}).get(
            "require_corpus_evidence", False
        )
    )
    answer = None
    llm_error = ""
    if args.llm:
        try:
            client = LLMClient(LLMConfig.from_env())
            cache = LLMCache(_root(args.data_root) / "llm-cache")
            answer = llm_answer_fn(client, cache)(args.question, hits)
        except LLMError as exc:
            llm_error = str(exc)
    if answer is not None:
        pass
    elif retriever.mode == "bm25":
        answer = answer_question(
            args.question,
            hits,
            min_score=min_score,
            min_matched=min_matched,
            extra_hits=policy_references,
            require_corpus=require_corpus,
        )
    elif retriever.gate_ok(args.question, min_score, min_matched):
        answer = answer_question(
            args.question,
            hits,
            min_score=0.0,
            min_matched=0,
            extra_hits=policy_references,
            require_corpus=require_corpus,
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
    if answer.abstained:
        try:
            claims_path = Path(args.pipeline).parent / "claims.yaml"
            claim = (
                classify(args.question, load_claims(claims_path))
                if claims_path.is_file()
                else {"nature": "general", "domain": "general"}
            )
            record_gap(
                _root(args.data_root) / "gaps.jsonl",
                args.question,
                answer.reason,
                str(claim.get("nature")),
                str(claim.get("domain")),
            )
        except (OSError, ValueError):
            pass

    if not answer.abstained:
        external_root = _root(args.data_root) / "external"
        try:
            ext_chunks, ext_manifest = load_chunks(external_root)
            ext_retriever = _retriever(
                ext_chunks, ext_manifest, args.pipeline, _lexicon_for(args), root=external_root
            )
            ext_hits = ext_retriever.search(args.question, top_k=3)
            answer = augment_with_external(answer, ext_hits)
        except (StoreError, DenseError, OSError):
            pass

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
                "llm": {"enabled": bool(args.llm), "error": llm_error},
                "reference": [hit.to_dict() for hit in references],
                "product_reference": [hit.to_dict() for hit in product_references],
                "policy_reference": [hit.to_dict() for hit in policy_references],
                "statistics": [hit.to_dict() for hit in statistics],
            }
        )
        return 0
    if args.llm and llm_error:
        print(f"llm unavailable, extractive fallback: {llm_error}", file=sys.stderr)
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
    today = date.fromisoformat(args.today) if args.today else None
    report = run_watch(Path(args.config), offline=args.offline)
    report["due"] = due_report(
        DEFAULT_CONFIG,
        REPO_ROOT / "configs" / "web-cards.yaml",
        REPO_ROOT / "configs" / "web-sources.yaml",
        today=today,
    )
    if args.propose:
        existing = load_candidates(Path(args.candidates)) if Path(args.candidates).is_file() else []
        report["proposals"] = propose_from_watch(report, existing, today=today)
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
    for row in report["due"]["corpus"]:
        print(f"due corpus {row['id']:24} {row['review_due']}")
    for row in report["due"]["cards"]:
        print(f"due card   {row['id']:24} {row['review_due']}")
    for proposal in report.get("proposals", []):
        print(f"proposal   {proposal['id']:24} {proposal['watch_ref']} {proposal['reason']}")
    return 0


def _sources_check(args: argparse.Namespace) -> int:
    today = date.fromisoformat(args.today) if args.today else date.today()
    registry = load_registry(Path(args.config))
    currency = check_currency(registry, today=today, grace_days=args.grace_days)
    candidates = check_candidates(Path(args.candidates), today=today, registry_ids=set(registry))
    report = {"currency": currency, "candidates": candidates}
    failed = bool(
        currency["overdue"] or currency["errors"] or candidates["expired"] or candidates["errors"]
    )
    if args.json:
        _print_json(report)
        return 1 if failed else 0
    print(
        f"sources {currency['sources']} today {currency['today']} "
        f"grace {currency['grace_days']}d overdue {len(currency['overdue'])}"
    )
    for row in currency["overdue"]:
        print(f"overdue    {row['id']:28} {row['review_due']} ({row['days_overdue']}d)")
    for error in currency["errors"]:
        print(f"error      {error}")
    print(
        f"candidates {candidates['total']} "
        f"open {candidates['counts'].get('open', 0)} "
        f"due {len(candidates['due'])} expired {len(candidates['expired'])}"
    )
    for row in candidates["due"]:
        print(f"due        {row['id']:28} open {row['days_open']}d")
    for row in candidates["expired"]:
        print(f"expired    {row['id']:28} {row['expires_at']} ({row['days_past']}d)")
    for error in candidates["errors"]:
        print(f"error      {error}")
    return 1 if failed else 0


def _sources_candidates(args: argparse.Namespace) -> int:
    today = date.fromisoformat(args.today) if args.today else date.today()
    items = load_candidates(Path(args.candidates))
    report = check_candidates(Path(args.candidates), today=today)
    if args.json:
        _print_json({"candidates": items, "check": report})
        return 0
    for item in items:
        print(
            f"{item['id']:16} {item['status']:9} {item['reason']:8} "
            f"{item.get('watch_ref') or '-':24} {item['url']}"
        )
    print(
        f"summary total {report['total']} open {report['counts'].get('open', 0)} "
        f"due {len(report['due'])} expired {len(report['expired'])}"
    )
    return 0


def _knowledge_list(args: argparse.Namespace) -> int:
    notes = list_notes(Path(args.dir))
    if args.json:
        _print_json({"notes": notes})
        return 0
    for note in notes:
        print(f"{note['id']:20} {note['topic']:12} {note['status']:9} {note['title'][:40]}")
    return 0


def _knowledge_check(args: argparse.Namespace) -> int:
    today = date.fromisoformat(args.today) if args.today else None
    report = check_knowledge(Path(args.dir), Path(args.cards), today=today, write=args.write)
    if args.json:
        _print_json(report)
        return 0
    for row in report["notes"]:
        mark = "due" if row["due"] else "   "
        reasons = "; ".join(row["reasons"])
        print(f"{row['id']:20} {row['status']:9} {mark} {reasons}".rstrip())
    print(f"summary {{'stale': {report['stale']}, 'due': {report['due']}}}")
    return 0


def _knowledge_gaps(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else data_root() / "gaps.jsonl"
    report = summarize_gaps(path)
    if args.json:
        _print_json(report)
    else:
        print(f"total {report['total']}")
        for field in ("nature", "domain", "reason"):
            print(f"{field}: {report['by_' + field]}")
    return 0


def _knowledge_approve(args: argparse.Namespace) -> int:
    result = approve_note(Path(args.dir), args.note_id)
    if args.json:
        _print_json(result)
    else:
        print(f"{result['id']} -> {result['status']}")
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
    answer_fn = None
    client = None
    cache = None
    if args.llm:
        client = LLMClient(LLMConfig.from_env())
        cache = LLMCache(_root(args.data_root) / "llm-cache")
        answer_fn = llm_answer_fn(client, cache)
    report = run_comparison(
        _root(args.data_root),
        Path(args.questions),
        Path(args.anchors),
        Path(args.pipeline),
        Path(args.lexicon),
        answer_fn=answer_fn,
    )
    anchor_config = load_anchors(Path(args.anchors))
    details = report.get("details", [])
    report["summary_split"] = {
        split: summarize([row for row in details if row.get("split") == split], [])
        for split in ("dev", "test")
    }
    report["summary_persona"] = {
        persona: summarize([row for row in details if row.get("persona") == persona], [])
        for persona in ("captain", "owner", "enforcement", "extension")
    }
    gold = anchor_config.get("gold") or {}
    checks = anchor_config.get("checks") or {}
    coverage = coverage_report(gold, checks, details)
    coverage["by_split"] = {}
    for split in ("dev", "test"):
        ids = {row["id"] for row in details if row.get("split") == split}
        coverage["by_split"][split] = coverage_report(
            {qid: value for qid, value in gold.items() if qid in ids},
            {qid: value for qid, value in checks.items() if qid in ids},
            [row for row in details if row["id"] in ids],
        )
    report["coverage"] = coverage
    if client is not None:
        gold = anchor_config.get("gold") or {}
        scored = []
        for row in report.get("details", []):
            if row["kind"] != "answerable":
                continue
            points = (gold.get(row["id"]) or {}).get("points") or []
            if not points:
                continue
            if row["abstained"]:
                score = {
                    "correctness": 0.0,
                    "completeness": 0.0,
                    "faithfulness": 0.0,
                    "reason": "abstained",
                }
            else:
                evidence = "\n".join(item.get("snippet", "") for item in row["answer"]["citations"])
                try:
                    score = score_answer(
                        row["question"],
                        points,
                        row["answer"]["answer"],
                        evidence,
                        client,
                        cache,
                    )
                except LLMError as exc:
                    score = {"error": str(exc)}
            scored.append(
                {
                    "id": row["id"],
                    "split": row.get("split"),
                    "persona": row.get("persona"),
                    "source": "model",
                    **score,
                }
            )
        review_meta: dict = {}
        if args.review:
            review = yaml.safe_load(Path(args.review).read_text(encoding="utf-8")) or {}
            overrides = review.get("questions") or {}
            for item in scored:
                override = overrides.get(item["id"]) or {}
                for name in ("correctness", "completeness", "faithfulness"):
                    if name in override:
                        item[name] = round(min(1.0, max(0.0, float(override[name]))), 4)
                if override:
                    item["source"] = "human"
                if override.get("note"):
                    item["note"] = str(override["note"])
            review_meta = {
                "reviewed_by": str(review.get("reviewed_by") or ""),
                "reviewed_at": str(review.get("reviewed_at") or ""),
            }
        numeric = [item for item in scored if "error" not in item]
        averages = {
            name: round(sum(item[name] for item in numeric) / len(numeric), 4) if numeric else 0.0
            for name in ("correctness", "completeness", "faithfulness")
        }
        averages_by_split: dict[str, dict[str, float]] = {}
        for split in ("dev", "test"):
            rows = [item for item in numeric if item.get("split") == split]
            averages_by_split[split] = {
                name: round(sum(item[name] for item in rows) / len(rows), 4) if rows else 0.0
                for name in ("correctness", "completeness", "faithfulness")
            }
        report["llm"] = {
            "model": client.config.model,
            "reasoning_effort": client.config.reasoning_effort,
            "prompt_version": SCORE_PROMPT_VERSION,
            "questions": scored,
            "averages": averages,
            "averages_by_split": averages_by_split,
            **review_meta,
        }
        if args.review_template:
            template = {
                "reviewed_by": "",
                "reviewed_at": str(date.today()),
                "questions": {
                    item["id"]: {
                        "correctness": item.get("correctness", 0.0),
                        "completeness": item.get("completeness", 0.0),
                        "faithfulness": item.get("faithfulness", 0.0),
                        "note": "",
                    }
                    for item in scored
                },
            }
            Path(args.review_template).write_text(
                yaml.safe_dump(template, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        hybrid = report["arms"].get("hybrid")
        if hybrid:
            hybrid["answer_mode"] = "llm"
            hybrid["extractive_faithfulness"] = hybrid.pop("faithfulness", 0.0)
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
    for split in ("dev", "test"):
        summary = (report.get("summary_split") or {}).get(split) or {}
        if not summary:
            continue
        print(
            f"{split:5} recall {summary['recall_hits']}/{summary['answerable_questions']} "
            f"mrr {summary['mrr']:.2f} "
            f"abstain {summary['abstained_tests']}/{summary['abstention_tests']} "
            f"false {summary['false_refusals']}"
        )
    coverage_summary = (report.get("coverage") or {}).get("summary") or {}
    if coverage_summary:
        print(
            f"coverage {coverage_summary.get('covered', 0)}/"
            f"{coverage_summary.get('points', 0)} "
            f"({coverage_summary.get('rate', 0.0):.2f})"
        )
    for split in ("dev", "test"):
        sub = ((report.get("coverage") or {}).get("by_split") or {}).get(split) or {}
        summary = sub.get("summary") or {}
        if summary:
            print(
                f"coverage {split:5} {summary.get('covered', 0)}/{summary.get('points', 0)} "
                f"({summary.get('rate', 0.0):.2f})"
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
    llm = report.get("llm")
    if llm:
        averages = llm["averages"]
        print(
            f"llm judge {llm['model']} correctness {averages['correctness']:.2f} "
            f"completeness {averages['completeness']:.2f} "
            f"faithfulness {averages['faithfulness']:.2f}"
        )
        for split, split_averages in (llm.get("averages_by_split") or {}).items():
            print(
                f"llm judge {split:5} correctness {split_averages['correctness']:.2f} "
                f"completeness {split_averages['completeness']:.2f} "
                f"faithfulness {split_averages['faithfulness']:.2f}"
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
    ingest_parser.add_argument("--knowledge-dir", default=None)
    ingest_parser.add_argument("--no-web", action="store_true")
    ingest_parser.add_argument("--no-knowledge", action="store_true")
    ingest_parser.add_argument("--external-only", action="store_true")
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
    ask_parser.add_argument("--llm", action="store_true", help="use the configured LLM")
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
    eval_parser.add_argument("--llm", action="store_true", help="use the configured LLM")
    eval_parser.add_argument("--review", default=None, help="human score override YAML")
    eval_parser.add_argument("--review-template", default=None, help="write a review template")
    eval_parser.add_argument("--json", action="store_true")
    eval_parser.set_defaults(func=_eval)

    watch_parser = subparsers.add_parser("watch", help="check the curated authoritative watch list")
    watch_parser.add_argument("--config", default=str(DEFAULT_WATCH))
    watch_parser.add_argument("--offline", action="store_true")
    watch_parser.add_argument("--report", default=None)
    watch_parser.add_argument("--propose", action="store_true", help="emit candidate proposals")
    watch_parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    watch_parser.add_argument("--today", default=None)
    watch_parser.add_argument("--json", action="store_true")
    watch_parser.set_defaults(func=_watch)

    sources_parser = subparsers.add_parser("sources", help="check source currency and candidates")
    sources_sub = sources_parser.add_subparsers(dest="sources_command", required=True)
    sources_check_parser = sources_sub.add_parser("check", help="enforce review dates")
    sources_check_parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    sources_check_parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    sources_check_parser.add_argument("--today", default=None)
    sources_check_parser.add_argument("--grace-days", type=int, default=30)
    sources_check_parser.add_argument("--json", action="store_true")
    sources_check_parser.set_defaults(func=_sources_check)
    sources_candidates_parser = sources_sub.add_parser("candidates", help="list candidates")
    sources_candidates_parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    sources_candidates_parser.add_argument("--today", default=None)
    sources_candidates_parser.add_argument("--json", action="store_true")
    sources_candidates_parser.set_defaults(func=_sources_candidates)

    knowledge_parser = subparsers.add_parser("knowledge", help="manage structured knowledge notes")
    knowledge_sub = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    list_parser = knowledge_sub.add_parser("list", help="list notes")
    list_parser.add_argument("--dir", default=str(REPO_ROOT / "configs" / "knowledge"))
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=_knowledge_list)
    check_parser = knowledge_sub.add_parser("check", help="validate notes and mark stale/expired")
    check_parser.add_argument("--dir", default=str(REPO_ROOT / "configs" / "knowledge"))
    check_parser.add_argument("--cards", default=str(REPO_ROOT / "configs" / "web-cards.yaml"))
    check_parser.add_argument("--today", default=None)
    check_parser.add_argument("--write", action="store_true")
    check_parser.add_argument("--json", action="store_true")
    check_parser.set_defaults(func=_knowledge_check)
    gaps_parser = knowledge_sub.add_parser("gaps", help="summarise refused questions")
    gaps_parser.add_argument("--path", default=None)
    gaps_parser.add_argument("--json", action="store_true")
    gaps_parser.set_defaults(func=_knowledge_gaps)
    approve_parser = knowledge_sub.add_parser("approve", help="approve a draft note")
    approve_parser.add_argument("note_id")
    approve_parser.add_argument("--dir", default=str(REPO_ROOT / "configs" / "knowledge"))
    approve_parser.add_argument("--json", action="store_true")
    approve_parser.set_defaults(func=_knowledge_approve)

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
        RegistryError,
        CandidateError,
        DenseError,
        StatsError,
        StoreError,
        WatchError,
        WebError,
        KnowledgeError,
        LLMError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
