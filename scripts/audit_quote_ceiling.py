#!/usr/bin/env python3
"""Retrieval-depth ceiling audit for the private acceptance instrument.

Eval-only diagnostic. It answers one question before any answer-side code
changes: if every retrieved chunk (or every section of every retrieved
document) were quoted verbatim, how much of the judgeable point set could be
covered at top-k, and how often would the expected document and location be
citable? The script never enters the product path, never writes the store and
never changes the scoring module.

Usage:
    SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... PYTHONPATH=src \
        python scripts/audit_quote_ceiling.py --task-id P11-MEAS-185 --depth 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
K_VALUES = (5, 10, 20, 30, 60, 100, 200)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def _norm(text: str) -> str:
    from scs_fkb.eval_accept.points import normalize

    return normalize(text)


def _section_rank(terms: list[str], hits: list[Any]) -> int | None:
    """First index where one cited section group contains every term.

    The scorer groups cited sentences by (document, section), so two chunks that
    share a section label can jointly satisfy a point.
    """
    if not terms:
        return None
    groups: dict[tuple[str, str], str] = {}
    for index, hit in enumerate(hits):
        chunk = hit.chunk
        key = (chunk.doc_id, chunk.section or "")
        groups[key] = groups.get(key, "") + "\n" + chunk.text
        if all(term in _norm(groups[key]) for term in terms):
            return index
    return None


def _document_rank(terms: list[str], hits: list[Any]) -> int | None:
    if not terms:
        return None
    groups: dict[str, str] = {}
    for index, hit in enumerate(hits):
        doc_id = hit.chunk.doc_id
        groups[doc_id] = groups.get(doc_id, "") + "\n" + hit.chunk.text
        if all(term in _norm(groups[doc_id]) for term in terms):
            return index
    return None


def _rule_rank(pattern: str, hits: list[Any]) -> int | None:
    for index, hit in enumerate(hits):
        if re.search(pattern, _norm(hit.chunk.text)):
            return index
    return None


def _point_rank(spec: Any, hits: list[Any]) -> int | None:
    from scs_fkb.eval_accept.points import rule_pattern

    if spec.rule:
        pattern = rule_pattern(spec.rule)
        return _rule_rank(pattern, hits) if pattern else None
    terms = [_norm(term) for term in spec.terms if term]
    if spec.mode == "document":
        return _document_rank(terms, hits)
    return _section_rank(terms, hits)


def _docblock_rank(terms: list[str], hits: list[Any], sections: dict[str, list[str]]) -> int | None:
    """First index where a retrieved document's full section set contains the point."""
    if not terms:
        return None
    seen: set[str] = set()
    for index, hit in enumerate(hits):
        doc_id = hit.chunk.doc_id
        if doc_id in seen:
            continue
        seen.add(doc_id)
        for text in sections.get(doc_id, []):
            if all(term in _norm(text) for term in terms):
                return index
    return None


def _docblock_rule_rank(
    pattern: str, hits: list[Any], sections: dict[str, list[str]]
) -> int | None:
    seen: set[str] = set()
    for index, hit in enumerate(hits):
        doc_id = hit.chunk.doc_id
        if doc_id in seen:
            continue
        seen.add(doc_id)
        for text in sections.get(doc_id, []):
            if re.search(pattern, _norm(text)):
                return index
    return None


def _expected_docs(
    row: dict[str, Any], docmap: Any, indexed: set[str]
) -> tuple[set[str], set[str], list[str]]:
    """Repository documents the instrument expects for a row.

    Returns (expected docs, expected docs that are not indexed, expected SCS ids).
    """
    docs: set[str] = set()
    unindexed: set[str] = set()
    scs_ids: list[str] = []
    for scs_id in row.get("scs_doc_ids") or []:
        if str(scs_id) == "未登记":
            continue
        entry = docmap.entries.get(str(scs_id))
        if entry is None or entry.covers not in ("full", "partial"):
            continue
        scs_ids.append(str(scs_id))
        for doc_id in entry.docs:
            docs.add(str(doc_id))
            if str(doc_id) not in indexed:
                unindexed.add(str(doc_id))
    return docs, unindexed, scs_ids


def _doc_rank(hits: list[Any], expected: set[str]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for index, hit in enumerate(hits):
        doc_id = hit.chunk.doc_id
        if doc_id in expected and doc_id not in ranks:
            ranks[doc_id] = index
    return ranks


def _location_rank(
    hits: list[Any],
    expected: set[str],
    row: dict[str, Any],
    anchor_terms: list[str],
    *,
    sections: dict[str, list[str]] | None = None,
) -> tuple[int | None, str]:
    """Approximate the scorer's location check against cited section text."""
    from scs_fkb.eval_accept.scoring import (
        _clean,
        _location_tokens,
        _requirement_locations,
        longest_common_substring,
    )

    locations = _requirement_locations(row)
    if not locations:
        return 0, "none"
    needles = [_clean(location) for location in locations]
    terms = [_norm(term) for term in anchor_terms if term]
    groups: dict[tuple[str, str], str] = {}
    seen_docs: set[str] = set()
    for index, hit in enumerate(hits):
        chunk = hit.chunk
        if chunk.doc_id not in expected:
            continue
        key = (chunk.doc_id, chunk.section or "")
        groups[key] = groups.get(key, "") + "\n" + chunk.text
        candidates = [(" ".join([chunk.section or "", groups[key]]), chunk.section or "")]
        if sections is not None and chunk.doc_id not in seen_docs:
            seen_docs.add(chunk.doc_id)
            candidates.extend(
                (" ".join([chunk.section or "", text]), chunk.section or "")
                for text in sections.get(chunk.doc_id, [])
            )
        for text, section in candidates:
            haystack = _clean(text)
            for location, needle in zip(locations, needles, strict=False):
                tokens = _location_tokens(location)
                if tokens:
                    matched = sum(1 for token in tokens if _clean(token) in haystack)
                    if matched >= 2 and matched / len(tokens) >= 0.5:
                        return index, "tokens"
                if longest_common_substring(needle, _clean(section)) >= 3:
                    return index, "lcs"
            if terms and any(term in _norm(text) for term in terms):
                return index, "anchor"
    return None, "unmatched"


def _ceiling(ranks: list[int | None], k: int) -> int:
    return sum(1 for rank in ranks if rank is not None and rank < k)


def _write_markdown(
    path: Path,
    *,
    total_points: int,
    rows: int,
    indexed: int,
    depth: int,
    by_k: dict[int, dict[str, int]],
    by_domain: list[dict[str, Any]],
    by_document: list[dict[str, Any]],
    unindexed_rows: int,
    unindexed_points: int,
    examples: list[dict[str, Any]],
) -> None:
    lines = [
        "# Retrieval-depth ceiling audit",
        "",
        f"- answerable rows: {rows}",
        f"- judgeable points: {total_points}",
        f"- indexed documents: {indexed}",
        f"- retriever depth per query: {depth}",
        f"- rows whose expected documents are not indexed: {unindexed_rows} "
        f"({unindexed_points} points)",
        "",
        "## Ceiling by retrieval depth",
        "",
        "| k | section groups | doc blocks | rows: expected doc | rows: location |",
        "|---:|---:|---:|---:|---:|",
    ]
    for k in K_VALUES:
        row = by_k.get(k) or {}
        point = row.get("points", 0) / total_points if total_points else 0.0
        block = row.get("blocks", 0) / total_points if total_points else 0.0
        lines.append(
            f"| {k} | {row.get('points', 0)} ({point:.4f}) | "
            f"{row.get('blocks', 0)} ({block:.4f}) | "
            f"{row.get('doc_rows', 0)} ({row.get('doc_rate', 0):.4f}) | "
            f"{row.get('loc_rows', 0)} ({row.get('loc_rate', 0):.4f}) |"
        )
    lines += [
        "",
        "## Points by domain (k=200)",
        "",
        "| Domain | Points | Section groups | Doc blocks |",
        "|---|---:|---:|---:|",
    ]
    for item in by_domain:
        lines.append(
            f"| {item['domain']} | {item['points']} | {item['covered']} | {item['blocks']} |"
        )
    lines += [
        "",
        "## Uncovered points by expected document (k=200)",
        "",
        "| Document | Points |",
        "|---|---:|",
    ]
    for item in by_document[:25]:
        lines.append(f"| {item['document']} | {item['points']} |")
    if examples:
        lines += ["", "## Uncovered point examples", ""]
        for item in examples[:20]:
            lines.append(
                f"- {item['id']} {item['expected']}: `{item['terms']}` — {item['point']}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT", ""))
    parser.add_argument("--task-id", default="P11-MEAS-185")
    parser.add_argument("--top-k", type=int, default=200)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        print("set --data-root and --run-root (or their environment variables)", file=sys.stderr)
        return 2

    from scs_fkb.eval_accept import load_dataset, load_docmap
    from scs_fkb.eval_accept.points import (
        ConceptSource,
        PointOverrides,
        point_specs,
        rule_pattern,
    )
    from scs_fkb.rag import LLMCache
    from scs_fkb.retrieve_v2.rewrite import rewrite
    from scs_fkb.service_v2 import build_service

    data_root = Path(args.data_root).expanduser()
    dataset_dir = data_root / "eval" / "acceptance"
    rows = [
        row
        for row in load_dataset(dataset_dir / "dataset.jsonl")
        if row.get("answerability") in ("可答", "部分可答")
    ]
    if args.limit:
        rows = rows[: args.limit]
    docmap = load_docmap(dataset_dir / "doc-map.yaml")
    concepts = ConceptSource.load(
        ROOT / "configs" / "terms.yaml", dataset_dir / "domain-terms.yaml"
    )
    overrides = PointOverrides.load(dataset_dir / "point-overrides.yaml")
    service = build_service(data_root=data_root, run_root=args.run_root)
    retriever = service.retriever
    retriever.depth = max(10, args.depth)

    client = None
    cache = LLMCache(data_root / "llm-cache")
    try:
        from scs_fkb.llm import LLMClient, LLMConfig

        client = LLMClient(LLMConfig.from_env())
    except Exception as exc:  # noqa: BLE001 - a missing key must not hide the audit
        print(f"rewrite client unavailable, using plain queries: {exc}", file=sys.stderr)

    chunks = _load_jsonl(data_root / "v2/processed/chunks.jsonl")
    indexed = {str(chunk["doc_id"]) for chunk in chunks}
    sections: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for chunk in chunks:
        doc_id = str(chunk["doc_id"])
        key = str(chunk.get("section") or "")
        sections[doc_id].setdefault(key, []).append(str(chunk["text"]))
    section_texts = {
        doc_id: [" ".join(texts) for texts in groups.values()]
        for doc_id, groups in sections.items()
    }

    point_ranks: list[int | None] = []
    block_ranks: list[int | None] = []
    doc_ranks: list[dict[str, int]] = []
    loc_ranks: list[int | None] = []
    row_expected: list[set[str]] = []
    domain_points: dict[str, list[int | None]] = defaultdict(list)
    domain_blocks: dict[str, list[int | None]] = defaultdict(list)
    uncovered_by_doc: Counter[str] = Counter()
    unindexed_docs: set[str] = set()
    unindexed_points = 0
    examples: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        question = str(row.get("question") or "")
        queries = rewrite(question, client, cache) if client is not None else []
        hits = retriever.search_queries([question, *queries], top_k=args.top_k)
        specs = point_specs(row, concepts=concepts, overrides=overrides)
        anchors = [term for spec in specs for term in spec.terms]
        expected, missed, scs_ids = _expected_docs(row, docmap, indexed)
        row_expected.append(expected)
        unindexed_docs |= missed
        doc_ranks.append(_doc_rank(hits, expected))
        location_rank, _source = _location_rank(
            hits, expected, row, anchors, sections=section_texts
        )
        loc_ranks.append(location_rank)
        for point_index, spec in enumerate(specs):
            if spec.skip:
                continue
            if not spec.terms and not spec.rule:
                continue
            rank = _point_rank(spec, hits)
            point_ranks.append(rank)
            terms = [_norm(term) for term in spec.terms if term]
            if spec.rule:
                pattern = rule_pattern(spec.rule)
                block = (
                    _docblock_rule_rank(pattern, hits, section_texts)
                    if pattern
                    else None
                )
            else:
                block = _docblock_rank(terms, hits, section_texts) if terms else None
            block_ranks.append(block)
            domain_points[str(row.get("domain") or "")].append(rank)
            domain_blocks[str(row.get("domain") or "")].append(block)
            if rank is None:
                if missed:
                    unindexed_points += 1
                for scs_id in scs_ids:
                    uncovered_by_doc[scs_id] += 1
                if len(examples) < 40:
                    examples.append(
                        {
                            "id": row["id"],
                            "expected": row.get("scs_doc_ids") or [],
                            "terms": list(spec.terms) or spec.rule,
                            "point": str((row.get("required_points") or [""])[point_index])[:120],
                        }
                    )
        if index % 50 == 0:
            print(f"scanned {index}/{len(rows)}", file=sys.stderr)

    total_points = len(point_ranks)
    rows_with_expected = [item for item in row_expected if item]
    by_k: dict[int, dict[str, int]] = {}
    for k in K_VALUES:
        doc_ok = sum(
            1
            for expected, ranks in zip(row_expected, doc_ranks, strict=False)
            if expected and any(ranks.get(doc) is not None and ranks[doc] < k for doc in expected)
        )
        loc_ok = sum(1 for rank in loc_ranks if rank is not None and rank < k)
        by_k[k] = {
            "points": _ceiling(point_ranks, k),
            "blocks": _ceiling(block_ranks, k),
            "doc_rows": doc_ok,
            "doc_rate": round(doc_ok / len(rows_with_expected), 4) if rows_with_expected else 0.0,
            "loc_rows": loc_ok,
            "loc_rate": round(loc_ok / len(rows_with_expected), 4) if rows_with_expected else 0.0,
        }

    by_domain = []
    for domain in sorted(domain_points):
        ranks = domain_points[domain]
        blocks = domain_blocks[domain]
        by_domain.append(
            {
                "domain": domain,
                "points": len(ranks),
                "covered": sum(1 for rank in ranks if rank is not None),
                "blocks": sum(1 for rank in blocks if rank is not None),
                "covered_at_30": sum(1 for rank in ranks if rank is not None and rank < 30),
            }
        )
    by_document = [
        {"document": document, "points": count}
        for document, count in uncovered_by_doc.most_common()
    ]
    unindexed_rows = sum(1 for expected in row_expected if expected and (expected & unindexed_docs))

    out_dir = Path(args.run_root).expanduser() / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "rows": len(rows),
        "points_total": total_points,
        "indexed_documents": len(indexed),
        "top_k": args.top_k,
        "depth": retriever.depth,
        "by_k": {str(k): value for k, value in by_k.items()},
        "by_domain": by_domain,
        "by_document": by_document,
        "unindexed_documents": sorted(unindexed_docs),
        "unindexed_rows": unindexed_rows,
        "unindexed_points": unindexed_points,
        "examples": examples,
    }
    (out_dir / "ceiling.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(
        out_dir / "ceiling.md",
        total_points=total_points,
        rows=len(rows),
        indexed=len(indexed),
        depth=retriever.depth,
        by_k=by_k,
        by_domain=by_domain,
        by_document=by_document,
        unindexed_rows=unindexed_rows,
        unindexed_points=unindexed_points,
        examples=examples,
    )
    print(
        f"points={total_points} rows={len(rows)} depth={retriever.depth} "
        f"section@30={by_k[30]['points'] / total_points:.4f} "
        f"section@200={by_k[200]['points'] / total_points:.4f} "
        f"blocks@30={by_k[30]['blocks'] / total_points:.4f} "
        f"doc_rate@30={by_k[30]['doc_rate']:.4f} loc_rate@30={by_k[30]['loc_rate']:.4f}"
    )
    print(f"report: {out_dir / 'ceiling.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
