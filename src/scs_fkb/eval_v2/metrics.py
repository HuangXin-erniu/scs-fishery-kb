from __future__ import annotations

import re
from typing import Any

CITATION_RE = re.compile(r"\[[A-Za-z0-9][A-Za-z0-9_-]*(?: p\.\d+)?(?: §[^\]]+)?\]")
SENTENCE_RE = re.compile(r"(?<=[。！？；])|\n+")
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
    "citation_resolution",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _bigrams(text: str) -> set[str]:
    clean = _normalize(text)
    return {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}


def _coverage(terms: list[str], answer: str) -> float:
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if term in answer)
    return hits / len(terms)


def _citations(row: dict[str, Any]) -> list[dict[str, Any]]:
    citations = row.get("citations") or []
    return [item if isinstance(item, dict) else item.model_dump() for item in citations]


def _expected_docs(row: dict[str, Any]) -> set[str]:
    return {
        str(item.get("doc") or "")
        for item in (row.get("expected") or {}).get("evidence") or []
        if item.get("doc")
    }


def faithfulness(row: dict[str, Any]) -> float:
    if row.get("abstained"):
        return 1.0
    sentences = [
        line.strip() for line in SENTENCE_RE.split(row.get("answer") or "") if line.strip()
    ]
    if not sentences:
        return 0.0
    cited = sum(1 for sentence in sentences if CITATION_RE.search(sentence))
    return cited / len(sentences)


def answer_relevancy(row: dict[str, Any]) -> float:
    expected = row.get("expected") or {}
    if expected.get("abstained"):
        return 1.0 if row.get("abstained") else 0.0
    overlap = _bigrams(row.get("question") or "") & _bigrams(row.get("answer") or "")
    question = _bigrams(row.get("question") or "")
    return len(overlap) / max(1, len(question))


def context_precision(row: dict[str, Any]) -> float:
    expected = row.get("expected") or {}
    if expected.get("abstained"):
        return 1.0 if row.get("abstained") else 0.0
    citations = _citations(row)
    if not citations:
        return 0.0
    docs = _expected_docs(row)
    relevant = sum(1 for item in citations if str(item.get("doc_id") or "") in docs)
    return relevant / len(citations)


def context_recall(row: dict[str, Any]) -> float:
    expected = row.get("expected") or {}
    if expected.get("abstained"):
        return 1.0 if row.get("abstained") else 0.0
    docs = _expected_docs(row)
    if not docs:
        return 0.0
    cited = {str(item.get("doc_id") or "") for item in _citations(row)}
    return len(docs & cited) / len(docs)


def answer_correctness(row: dict[str, Any]) -> float:
    expected = row.get("expected") or {}
    if expected.get("abstained"):
        return 1.0 if row.get("abstained") else 0.0
    if row.get("abstained"):
        return 0.0
    terms = [str(term) for term in expected.get("terms") or []]
    answer = str(row.get("answer") or "")
    term_score = _coverage(terms, answer) if terms else 0.0
    gold = str(expected.get("answer") or "")
    gold_bigrams = _bigrams(gold)
    recall = len(_bigrams(answer) & gold_bigrams) / max(1, len(gold_bigrams))
    return max(term_score, recall)


def citation_resolution(row: dict[str, Any]) -> float:
    citations = _citations(row)
    if not citations:
        return 1.0 if row.get("abstained") else 0.0
    for item in citations:
        if not str(item.get("doc_id") or "").strip():
            return 0.0
        page = item.get("page")
        if not (item.get("section") or page is not None or item.get("url")):
            return 0.0
    return 1.0


def abstention_accuracy(row: dict[str, Any]) -> float | None:
    expected = row.get("expected") or {}
    if not expected.get("abstained"):
        return None
    return 1.0 if row.get("abstained") else 0.0


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    scored = {
        "faithfulness": faithfulness(row),
        "answer_relevancy": answer_relevancy(row),
        "context_precision": context_precision(row),
        "context_recall": context_recall(row),
        "answer_correctness": answer_correctness(row),
        "citation_resolution": citation_resolution(row),
    }
    abstention = abstention_accuracy(row)
    if abstention is not None:
        scored["abstention_accuracy"] = abstention
    return scored


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"questions": 0}
    summary: dict[str, Any] = {"questions": len(rows)}
    for name in METRIC_NAMES:
        values = [float(row[name]) for row in rows if name in row]
        summary[name] = round(sum(values) / len(values), 4) if values else 0.0
    abstention = [float(row["abstention_accuracy"]) for row in rows if "abstention_accuracy" in row]
    summary["abstention_accuracy"] = (
        round(sum(abstention) / len(abstention), 4) if abstention else None
    )
    summary["abstained"] = sum(1 for row in rows if row.get("abstained"))
    summary["mean_latency_ms"] = round(
        sum(float(row.get("latency_ms") or 0) for row in rows) / len(rows), 1
    )
    return summary


def gate_ok(summary: dict[str, Any], thresholds: dict[str, float]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for key, minimum in thresholds.items():
        value = summary.get(key)
        if value is None or float(value) < float(minimum):
            failures.append(f"{key}={value} < {minimum}")
    return not failures, failures


__all__ = [
    "METRIC_NAMES",
    "aggregate",
    "answer_correctness",
    "answer_relevancy",
    "citation_resolution",
    "context_precision",
    "context_recall",
    "faithfulness",
    "gate_ok",
    "score_row",
]
