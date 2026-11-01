from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .answer import answer_question, validate_citations
from .bm25 import BM25Index
from .lexicon import expand_query
from .reference import lookup as reference_lookup
from .store import load_chunks
from .text import tokenize

QUESTION_ID_RE = re.compile(r"Q-[EM]\d{2}")
DEFINITION_IDS = {"Q-E05", "Q-M04"}


def parse_questions(path: Path) -> list[dict[str, Any]]:
    """Read the question table from docs/questions.md."""
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not QUESTION_ID_RE.fullmatch(cells[0]):
            continue
        rows.append(
            {
                "id": cells[0],
                "question": cells[2],
                "type": cells[3],
                "evidence": cells[4],
            }
        )
    return rows


def load_anchors(path: Path) -> dict[str, Any]:
    """Read the gold anchors and the abstention list."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"eval config must be a mapping: {path}")
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported eval schema_version in {path}")
    anchors = data.get("anchors")
    if not isinstance(anchors, dict) or not anchors:
        raise ValueError(f"eval config lists no anchors: {path}")
    for question_id, entries in anchors.items():
        if not QUESTION_ID_RE.fullmatch(str(question_id)):
            raise ValueError(f"invalid question id in eval config: {question_id}")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{question_id} has no anchors")
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("doc"):
                raise ValueError(f"{question_id} has a malformed anchor")
    abstention = data.get("abstention") or []
    if not isinstance(abstention, list):
        raise ValueError(f"abstention must be a list in {path}")
    reference = data.get("reference") or []
    if not isinstance(reference, list):
        raise ValueError(f"reference must be a list in {path}")
    for item in reference:
        if not isinstance(item, dict) or not item.get("id") or not item.get("docs"):
            raise ValueError(f"malformed reference entry in {path}: {item}")
    return {
        "anchors": anchors,
        "abstention": [str(item) for item in abstention],
        "reference": reference,
    }


def anchor_matches(chunk, anchor: dict[str, Any]) -> bool:
    """A chunk matches when doc, page and section agree with the anchor."""
    if chunk.doc_id != anchor.get("doc"):
        return False
    page = anchor.get("page")
    if page is not None and chunk.page != int(page):
        return False
    section = anchor.get("section")
    if section and not chunk.section.startswith(str(section)):
        return False
    return True


def title_tokens(documents: list[dict[str, Any]]) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = {}
    for document in documents:
        title = document.get("title_zh") or document.get("title") or ""
        titles[str(document["doc_id"])] = set(tokenize(title))
    return titles


def summarize_reference(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = sum(1 for row in rows if row["hit"])
    return {
        "reference_questions": len(rows),
        "reference_hits": hits,
        "reference_rate": round(hits / len(rows), 4) if rows else 0.0,
    }


def summarize(results: list[dict[str, Any]], skipped: list[str]) -> dict[str, Any]:
    answerable = [row for row in results if row["kind"] == "answerable"]
    abstention = [row for row in results if row["kind"] == "abstention"]
    answered = [row for row in answerable if not row["abstained"]]
    recalled = sum(1 for row in answerable if row["hit"])
    refused = sum(1 for row in abstention if row["abstained"])
    resolved = sum(1 for row in answered if row["citation_valid"])
    return {
        "answerable_questions": len(answerable),
        "abstention_tests": len(abstention),
        "skipped_questions": len(skipped),
        "recall_hits": recalled,
        "recall_at_5": round(recalled / len(answerable), 4) if answerable else 0.0,
        "abstained_tests": refused,
        "abstention_rate": round(refused / len(abstention), 4) if abstention else 0.0,
        "false_refusals": len(answerable) - len(answered),
        "answered": len(answered),
        "citation_resolution": round(resolved / len(answered), 4) if answered else 0.0,
    }


def evaluate(
    questions_path: Path,
    anchors_path: Path,
    data_root: Path,
    min_score: float = 0.0,
    min_matched: int = 3,
    top_k: int = 5,
    title_boost: float = 0.0,
    lexicon: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score retrieval at anchor level and check abstinence and citations."""
    rows = {row["id"]: row for row in parse_questions(questions_path)}
    config = load_anchors(anchors_path)
    chunks, manifest = load_chunks(data_root)
    index = BM25Index(
        chunks,
        titles=title_tokens(manifest["documents"]),
        title_boost=title_boost,
    )
    results: list[dict[str, Any]] = []

    for question_id, anchors in config["anchors"].items():
        row = rows.get(question_id)
        if row is None:
            raise ValueError(f"anchor question is missing from the question table: {question_id}")
        query = expand_query(row["question"], lexicon) if lexicon else row["question"]
        hits = index.search(query, top_k=top_k)
        matched = [
            anchor for anchor in anchors if any(anchor_matches(hit.chunk, anchor) for hit in hits)
        ]
        answer = answer_question(
            row["question"],
            hits,
            min_score=min_score,
            min_matched=min_matched,
        )
        citation_valid = True
        if not answer.abstained:
            citation_valid, _ = validate_citations(answer.text, hits)
        results.append(
            {
                "id": question_id,
                "kind": "answerable",
                "question": row["question"],
                "anchors": anchors,
                "top": [
                    {
                        "doc": hit.chunk.doc_id,
                        "page": hit.chunk.page,
                        "section": hit.chunk.section,
                        "score": round(hit.score, 6),
                    }
                    for hit in hits
                ],
                "hit": bool(matched),
                "matched_anchors": matched,
                "abstained": answer.abstained,
                "reason": answer.reason,
                "citation_valid": citation_valid,
            }
        )

    for question_id in config["abstention"]:
        row = rows.get(question_id)
        if row is None:
            raise ValueError(
                f"abstention question is missing from the question table: {question_id}"
            )
        query = expand_query(row["question"], lexicon) if lexicon else row["question"]
        hits = index.search(query, top_k=top_k)
        answer = answer_question(
            row["question"],
            hits,
            min_score=min_score,
            min_matched=min_matched,
        )
        results.append(
            {
                "id": question_id,
                "kind": "abstention",
                "question": row["question"],
                "anchors": [],
                "top": [
                    {
                        "doc": hit.chunk.doc_id,
                        "page": hit.chunk.page,
                        "section": hit.chunk.section,
                        "score": round(hit.score, 6),
                    }
                    for hit in hits
                ],
                "hit": None,
                "matched_anchors": [],
                "abstained": answer.abstained,
                "reason": answer.reason,
                "citation_valid": True,
            }
        )

    reference_results: list[dict[str, Any]] = []
    for item in config.get("reference", []):
        question_id = str(item["id"])
        row = rows.get(question_id)
        if row is None:
            raise ValueError(
                f"reference question is missing from the question table: {question_id}"
            )
        hits = reference_lookup(row["question"], root=data_root)
        expected = [str(doc) for doc in item["docs"]]
        reference_results.append(
            {
                "id": question_id,
                "expected_docs": expected,
                "top": [{"doc": hit.chunk.doc_id, "score": round(hit.score, 6)} for hit in hits],
                "hit": any(hit.chunk.doc_id in expected for hit in hits),
            }
        )

    selected = set(config["anchors"]) | set(config["abstention"])
    skipped = [
        {
            "id": question_id,
            "reason": (
                "no explicit definition in the corpus"
                if question_id in DEFINITION_IDS
                else "no gold anchor in the current index"
            ),
        }
        for question_id in rows
        if question_id not in selected
    ]
    skipped_ids = [item["id"] for item in skipped]

    return {
        "schema_version": 1,
        "index_version": manifest.get("index_version"),
        "top_k": top_k,
        "min_score": min_score,
        "min_matched": min_matched,
        "title_boost": title_boost,
        "lexicon": bool(lexicon),
        "summary": {
            **summarize(results, skipped_ids),
            **summarize_reference(reference_results),
        },
        "results": results,
        "reference": reference_results,
        "skipped": skipped,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
