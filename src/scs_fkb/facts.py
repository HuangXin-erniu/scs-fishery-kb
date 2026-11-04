from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .chunking import chunk_document
from .config import DEFAULT_CONFIG, REPO_ROOT
from .models import Chunk, Document
from .parsers import Page as ParsedPage
from .registry import load_registry
from .store import load_chunks

DEFAULT_FACTS_DIR = REPO_ROOT / "configs" / "facts"
FACT_ID = re.compile(r"FACT-[A-Z]+-\d{3}")
KINDS = frozenset({"atomic", "provision"})
QUESTION_CLASSES = frozenset(
    {
        "time_range",
        "scope",
        "operation_type",
        "materials",
        "procedure",
        "penalty",
        "inspection",
        "quantity",
        "definition",
        "status",
    }
)
TOPICS = frozenset({"policy", "gear", "stats", "environment", "hazard", "species"})
STATUSES = frozenset({"draft", "approved", "stale", "superseded"})
CONFIDENCE = frozenset({"high", "medium", "low"})
REQUIRED = (
    "id",
    "kind",
    "topic",
    "question_class",
    "subject",
    "predicate",
    "value",
    "evidence",
    "source",
    "status",
    "confidence",
    "as_of",
    "review_due",
)


class FactError(RuntimeError):
    """Raised when a fact file or entry is malformed."""


def normalize(text: str) -> str:
    return " ".join(str(text).split())


def _iso(value: Any, field: str, fact_id: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise FactError(f"{fact_id}: {field} is not an ISO date") from exc


def validate_fact(fact: dict[str, Any]) -> list[str]:
    if not isinstance(fact, dict):
        return ["fact is not a mapping"]
    fact_id = str(fact.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in fact:
            errors.append(f"{fact_id}: missing {key}")
    if not FACT_ID.fullmatch(fact_id):
        errors.append(f"{fact_id}: id must match FACT-<TOPIC>-<NNN>")
    if fact.get("kind") not in KINDS:
        errors.append(f"{fact_id}: kind {fact.get('kind')!r} not in {sorted(KINDS)}")
    if fact.get("topic") not in TOPICS:
        errors.append(f"{fact_id}: topic {fact.get('topic')!r} not in {sorted(TOPICS)}")
    if fact.get("question_class") not in QUESTION_CLASSES:
        errors.append(
            f"{fact_id}: question_class {fact.get('question_class')!r} "
            f"not in {sorted(QUESTION_CLASSES)}"
        )
    for key in ("subject", "predicate", "value", "evidence"):
        if key in fact and not str(fact.get(key) or "").strip():
            errors.append(f"{fact_id}: {key} is empty")
    if fact.get("status") not in STATUSES:
        errors.append(f"{fact_id}: status {fact.get('status')!r} not in {sorted(STATUSES)}")
    if fact.get("confidence") not in CONFIDENCE:
        errors.append(
            f"{fact_id}: confidence {fact.get('confidence')!r} not in {sorted(CONFIDENCE)}"
        )
    source = fact.get("source")
    if not isinstance(source, dict):
        errors.append(f"{fact_id}: source is not a mapping")
    else:
        if not str(source.get("doc") or "").strip():
            errors.append(f"{fact_id}: source.doc is empty")
        sha = str(source.get("sha256") or "")
        if sha and not re.fullmatch(r"[0-9a-f]{64}", sha):
            errors.append(f"{fact_id}: source.sha256 is not a sha256")
        if source.get("section") is not None and not str(source.get("section")).strip():
            errors.append(f"{fact_id}: source.section is empty")
    try:
        as_of = _iso(fact.get("as_of"), "as_of", fact_id)
        review_due = _iso(fact.get("review_due"), "review_due", fact_id)
        if review_due < as_of:
            errors.append(f"{fact_id}: review_due is before as_of")
    except FactError as exc:
        errors.append(str(exc))
    effective = fact.get("effective")
    if effective is not None:
        if not isinstance(effective, dict):
            errors.append(f"{fact_id}: effective is not a mapping")
        else:
            dates: dict[str, date] = {}
            for key in ("from", "to"):
                value = effective.get(key)
                if value in (None, ""):
                    continue
                try:
                    dates[key] = date.fromisoformat(str(value))
                except ValueError:
                    errors.append(f"{fact_id}: effective.{key} is not an ISO date")
            if "from" in dates and "to" in dates and dates["to"] < dates["from"]:
                errors.append(f"{fact_id}: effective.to is before effective.from")
    supersedes = fact.get("supersedes")
    if supersedes is not None and not FACT_ID.fullmatch(str(supersedes)):
        errors.append(f"{fact_id}: supersedes is not a fact id")
    return errors


def load_facts(path: Path | str) -> list[dict[str, Any]]:
    fact_path = Path(path)
    if not fact_path.is_file():
        raise FactError(f"fact file not found: {fact_path}")
    data = yaml.safe_load(fact_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise FactError(f"unsupported fact schema: {fact_path}")
    items = data.get("facts")
    if not isinstance(items, list):
        raise FactError(f"facts is not a list: {fact_path}")
    errors: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{fact_path}: entry is not a mapping")
            continue
        fact_id = str(item.get("id") or "<unknown>")
        errors.extend(validate_fact(item))
        if fact_id in seen:
            errors.append(f"{fact_id}: duplicate id")
        seen.add(fact_id)
    if errors:
        raise FactError("; ".join(errors))
    return items


def load_all(directory: Path | str = DEFAULT_FACTS_DIR) -> list[dict[str, Any]]:
    fact_dir = Path(directory)
    if not fact_dir.is_dir():
        raise FactError(f"fact directory not found: {fact_dir}")
    rows: list[dict[str, Any]] = []
    for path in sorted(fact_dir.glob("*.yaml")):
        for fact in load_facts(path):
            rows.append({**fact, "_path": path})
    return rows


def _overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    a = left.get("effective") or {}
    b = right.get("effective") or {}
    a_from = str(a.get("from") or "0000-01-01")
    a_to = str(a.get("to") or "9999-12-31")
    b_from = str(b.get("from") or "0000-01-01")
    b_to = str(b.get("to") or "9999-12-31")
    return a_from <= b_to and b_from <= a_to


def _registry_meta(registry_path: Path | str) -> dict[str, dict[str, Any]]:
    return load_registry(registry_path)


def check_facts(
    directory: Path | str = DEFAULT_FACTS_DIR,
    *,
    data_root: Path | str,
    registry_path: Path | str = DEFAULT_CONFIG,
    today: date | None = None,
) -> dict[str, Any]:
    current = today or date.today()
    facts = load_all(directory)
    registry = _registry_meta(registry_path)
    chunks, _manifest = load_chunks(Path(data_root))
    errors: list[str] = []
    conflicts: list[str] = []
    expired: list[dict[str, str]] = []
    due: list[dict[str, str]] = []
    approved: list[dict[str, Any]] = []
    for fact in facts:
        fact_id = str(fact["id"])
        source = fact.get("source") or {}
        doc_id = str(source.get("doc") or "")
        section = str(source.get("section") or "")
        meta = registry.get(doc_id)
        if meta is None:
            errors.append(f"{fact_id}: source doc {doc_id!r} is not in the registry")
            continue
        if str(source.get("sha256") or "") != str(meta.get("hash") or ""):
            errors.append(f"{fact_id}: source hash does not match the registry for {doc_id}")
        if fact.get("status") == "approved":
            if meta.get("authority_tier") not in {"A", "B"}:
                errors.append(f"{fact_id}: approved fact needs an A/B source")
            if meta.get("license") not in {"public", "cc-by-nc-sa-3.0-igo"}:
                errors.append(f"{fact_id}: approved fact needs a public licence")
        evidence = normalize(str(fact.get("evidence") or ""))
        candidates = [
            chunk
            for chunk in chunks
            if chunk.doc_id == doc_id and (not section or chunk.section.startswith(section))
        ]
        if not any(evidence and evidence in normalize(chunk.text) for chunk in candidates):
            errors.append(f"{fact_id}: evidence is not a verbatim substring of {doc_id} {section}")
        review_due = date.fromisoformat(str(fact["review_due"]))
        if fact.get("status") == "approved":
            approved.append(fact)
        if review_due < current:
            expired.append({"id": fact_id, "review_due": review_due.isoformat()})
        elif (review_due - current).days <= 30:
            due.append({"id": fact_id, "review_due": review_due.isoformat()})
    for index, left in enumerate(approved):
        for right in approved[index + 1 :]:
            if left.get("question_class") != right.get("question_class"):
                continue
            if left.get("subject") != right.get("subject"):
                continue
            if left.get("predicate") != right.get("predicate"):
                continue
            if left.get("jurisdiction") != right.get("jurisdiction"):
                continue
            if str(left.get("value")) == str(right.get("value")):
                continue
            if left.get("supersedes") == right.get("id") or right.get("supersedes") == left.get(
                "id"
            ):
                continue
            if _overlap(left, right):
                conflicts.append(f"{left['id']} conflicts with {right['id']}")
    return {
        "facts": len(facts),
        "approved": len(approved),
        "draft": sum(1 for fact in facts if fact.get("status") == "draft"),
        "errors": errors,
        "conflicts": conflicts,
        "expired": expired,
        "due": due,
        "today": current.isoformat(),
    }


def fact_text(fact: dict[str, Any]) -> str:
    source = fact.get("source") or {}
    parts = [
        f"{fact['subject']}：{fact['predicate']}",
        str(fact["value"]),
    ]
    effective = fact.get("effective") or {}
    if effective:
        parts.append(
            f"生效：{effective.get('from') or '未注明'} 至 {effective.get('to') or '现行'}"
        )
    parts.append(f"依据：{source.get('doc')} §{source.get('section') or '全文'}")
    return "\n".join(parts)


def fact_documents(
    directory: Path | str,
    *,
    data_root: Path | str,
    registry_path: Path | str = DEFAULT_CONFIG,
    today: date | None = None,
    max_fallback_chars: int = 800,
) -> tuple[list[Document], list[Chunk], list[dict[str, Any]], dict[str, int]]:
    current = today or date.today()
    facts = load_all(directory)
    registry = _registry_meta(registry_path)
    documents: list[Document] = []
    chunks: list[Chunk] = []
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for fact in facts:
        if fact.get("status") != "approved":
            continue
        if date.fromisoformat(str(fact["review_due"])) < current:
            continue
        source = fact.get("source") or {}
        meta = registry.get(str(source.get("doc"))) or {}
        text = fact_text(fact)
        document = Document(
            doc_id=str(fact["id"]),
            source_id=str(source.get("doc") or ""),
            title=str(fact["subject"]),
            title_zh=str(fact["subject"]),
            publisher=str(meta.get("publisher") or ""),
            year=None,
            doc_type="fact",
            sensitivity="public",
            language="zh",
            page_count=1,
            file_hash=str(source.get("sha256") or ""),
        )
        page = ParsedPage(number=0, lines=text.splitlines())
        made = [
            replace(
                chunk,
                kind="fact",
                source_class=str(meta.get("source_class") or ""),
                trust="authoritative"
                if meta.get("source_class") in {"normative", "official_statistics"}
                else "standard",
                review_due=str(fact["review_due"]),
            )
            for chunk in chunk_document(document, [page], max_fallback_chars)
        ]
        if not made:
            continue
        documents.append(document)
        chunks.extend(made)
        counts[document.doc_id] = len(made)
        entries.append(
            {
                "id": document.doc_id,
                "hash": document.file_hash,
                "location": f"facts/{fact['_path'].name}",
                "format": "fact",
                "pages": 1,
                "chunks": len(made),
                "kind": "fact",
            }
        )
    return documents, chunks, entries, counts


__all__ = [
    "DEFAULT_FACTS_DIR",
    "FactError",
    "check_facts",
    "fact_documents",
    "fact_text",
    "load_all",
    "load_facts",
    "validate_fact",
]
