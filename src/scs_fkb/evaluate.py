from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .answer import answer_question, validate_citations
from .bm25 import BM25Index
from .store import load_chunks

QUESTION_ID_RE = re.compile(r"Q-[EM]\d{2}")
EVIDENCE_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b")
ABSTAIN_MARKER = "none registered"


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
                "evidence_ids": EVIDENCE_ID_RE.findall(cells[4]),
            }
        )
    return rows


def select_questions(
    rows: list[dict[str, Any]],
    document_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the draft set into M1 questions, abstention tests and skipped rows."""
    documents = set(document_ids)
    m1: list[dict[str, Any]] = []
    abstention: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        if row["evidence_ids"] and documents & set(row["evidence_ids"]):
            m1.append(row)
        elif ABSTAIN_MARKER in row["evidence"].lower():
            abstention.append(row)
        else:
            skipped.append(row)
    return m1, abstention, skipped


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in results if row["kind"] == "answerable"]
    abstention = [row for row in results if row["kind"] == "abstention"]
    answered = [row for row in answerable if not row["abstained"]]
    recalled = sum(1 for row in answerable if row["retrieved"])
    refused = sum(1 for row in abstention if row["abstained"])
    resolved = sum(1 for row in answered if row["citation_valid"])
    return {
        "answerable_questions": len(answerable),
        "abstention_tests": len(abstention),
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
    data_root: Path,
    document_ids: list[str],
    min_score: float = 0.0,
    min_matched: int = 3,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run retrieval and the answer gate over the M1 questions."""
    rows = parse_questions(questions_path)
    m1, abstention, skipped = select_questions(rows, document_ids)
    chunks, manifest = load_chunks(data_root)
    index = BM25Index(chunks)
    results: list[dict[str, Any]] = []

    for row in m1:
        hits = index.search(row["question"], top_k=top_k)
        docs = [hit.chunk.doc_id for hit in hits]
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
                "id": row["id"],
                "kind": "answerable",
                "question": row["question"],
                "expected": row["evidence_ids"],
                "top_docs": docs,
                "scores": [round(hit.score, 6) for hit in hits],
                "retrieved": bool(set(docs) & set(row["evidence_ids"])),
                "abstained": answer.abstained,
                "reason": answer.reason,
                "citation_valid": citation_valid,
            }
        )

    for row in abstention:
        hits = index.search(row["question"], top_k=top_k)
        answer = answer_question(
            row["question"],
            hits,
            min_score=min_score,
            min_matched=min_matched,
        )
        results.append(
            {
                "id": row["id"],
                "kind": "abstention",
                "question": row["question"],
                "expected": [],
                "top_docs": [hit.chunk.doc_id for hit in hits],
                "scores": [round(hit.score, 6) for hit in hits],
                "retrieved": None,
                "abstained": answer.abstained,
                "reason": answer.reason,
                "citation_valid": True,
            }
        )

    return {
        "schema_version": 1,
        "index_version": manifest.get("index_version"),
        "documents": list(document_ids),
        "top_k": top_k,
        "min_score": min_score,
        "min_matched": min_matched,
        "summary": summarize(results),
        "results": results,
        "skipped": [row["id"] for row in skipped],
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
