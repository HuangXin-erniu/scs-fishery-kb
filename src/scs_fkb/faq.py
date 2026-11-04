from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from .chunking import chunk_document
from .config import REPO_ROOT
from .facts import DEFAULT_FACTS_DIR
from .facts import load_all as load_facts
from .models import Chunk, Document
from .parsers import Page as ParsedPage

DEFAULT_FAQ = REPO_ROOT / "configs" / "faq.yaml"
FAQ_ID = re.compile(r"FAQ-[A-Z]+-\d{3}")
PERSONAS = frozenset({"captain", "owner", "enforcement", "extension"})
STATUSES = frozenset({"draft", "approved"})
REQUIRED = ("id", "question", "persona", "claims", "source", "status")


class FaqError(RuntimeError):
    """Raised when a FAQ file is malformed."""


def validate_faq(item: dict[str, Any]) -> list[str]:
    if not isinstance(item, dict):
        return ["faq is not a mapping"]
    faq_id = str(item.get("id") or "<unknown>")
    errors: list[str] = []
    for key in REQUIRED:
        if key not in item:
            errors.append(f"{faq_id}: missing {key}")
    if not FAQ_ID.fullmatch(faq_id):
        errors.append(f"{faq_id}: id must match FAQ-<PERSONA>-<NNN>")
    if not str(item.get("question") or "").strip():
        errors.append(f"{faq_id}: question is empty")
    if item.get("persona") not in PERSONAS:
        errors.append(f"{faq_id}: persona {item.get('persona')!r} is invalid")
    claims = item.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append(f"{faq_id}: claims must be a non-empty list")
    elif any(not str(claim).strip() for claim in claims):
        errors.append(f"{faq_id}: claims contain an empty value")
    if item.get("status") not in STATUSES:
        errors.append(f"{faq_id}: status {item.get('status')!r} is invalid")
    source = item.get("source")
    if not isinstance(source, dict):
        errors.append(f"{faq_id}: source is not a mapping")
    elif source.get("kind") not in {"public", "corpus"}:
        errors.append(f"{faq_id}: source.kind {source.get('kind')!r} is invalid")
    return errors


def load_faqs(path: Path | str = DEFAULT_FAQ) -> list[dict[str, Any]]:
    faq_path = Path(path)
    if not faq_path.is_file():
        raise FaqError(f"faq file not found: {faq_path}")
    data = yaml.safe_load(faq_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise FaqError(f"unsupported faq schema: {faq_path}")
    items = data.get("faqs")
    if not isinstance(items, list):
        raise FaqError(f"faqs is not a list: {faq_path}")
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{faq_path}: entry is not a mapping")
            continue
        faq_id = str(item.get("id") or "<unknown>")
        errors.extend(validate_faq(item))
        if faq_id in seen_ids:
            errors.append(f"{faq_id}: duplicate id")
        seen_ids.add(faq_id)
        question = str(item.get("question") or "")
        if question in seen_questions:
            errors.append(f"{faq_id}: duplicate question")
        seen_questions.add(question)
    if errors:
        raise FaqError("; ".join(errors))
    return items


def check_faqs(
    path: Path | str = DEFAULT_FAQ,
    *,
    facts_dir: Path | str = DEFAULT_FACTS_DIR,
) -> dict[str, Any]:
    faqs = load_faqs(path)
    facts = {str(fact["id"]): fact for fact in load_facts(facts_dir)}
    errors: list[str] = []
    approved = 0
    for item in faqs:
        faq_id = str(item["id"])
        for claim in item.get("claims") or []:
            fact = facts.get(str(claim))
            if fact is None:
                errors.append(f"{faq_id}: claim {claim!r} is not a fact")
            elif item.get("status") == "approved" and fact.get("status") != "approved":
                errors.append(f"{faq_id}: approved FAQ claims non-approved fact {claim}")
        if item.get("status") == "approved":
            approved += 1
    return {"faqs": len(faqs), "approved": approved, "errors": errors}


def faq_text(item: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"问：{item['question']}",
            "答：" + "；".join(str(claim) for claim in item.get("claims") or []),
            f"适用：{item['persona']}",
        ]
    )


def faq_documents(
    path: Path | str = DEFAULT_FAQ,
    *,
    max_fallback_chars: int = 800,
) -> tuple[list[Document], list[Chunk], list[dict[str, Any]], dict[str, int]]:
    faqs = load_faqs(path)
    documents: list[Document] = []
    chunks: list[Chunk] = []
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for item in faqs:
        if item.get("status") != "approved":
            continue
        text = faq_text(item)
        document = Document(
            doc_id=str(item["id"]),
            source_id=str(item["id"]),
            title=str(item["question"]),
            title_zh=str(item["question"]),
            publisher="public FAQ",
            year=None,
            doc_type="faq",
            sensitivity="public",
            language="zh",
            page_count=1,
            file_hash="",
        )
        page = ParsedPage(number=0, lines=text.splitlines())
        made = [
            replace(chunk, kind="faq", source_class="reference", trust="standard", review_due="")
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
                "hash": "",
                "location": "faq.yaml",
                "format": "faq",
                "pages": 1,
                "chunks": len(made),
                "kind": "faq",
            }
        )
    return documents, chunks, entries, counts


__all__ = [
    "DEFAULT_FAQ",
    "FaqError",
    "check_faqs",
    "faq_documents",
    "load_faqs",
    "validate_faq",
]
