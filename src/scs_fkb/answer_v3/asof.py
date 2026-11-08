from __future__ import annotations

import re
from datetime import date
from typing import Any

from .contract import AsOf, VersionNote

YEAR_CUE = re.compile(
    r"今年|现在|目前|最新|当年|现行|本年度|有效期|多久|几年|是否还|还有|近年|这两年|20\d{2}\s*年"
)


def _cn_date(value: str) -> str:
    text = str(value or "").strip()
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        return f"{match.group(1)}年{int(match.group(2))}月{int(match.group(3))}日"
    return text


def fallback(question: str) -> str:
    """State the knowledge-base as-of date for a time-sensitive question without a citation."""
    if not YEAR_CUE.search(question):
        return ""
    return f"知识库截至{date.today().year}年版现行有效"


def detect(question: str, doc_ids: list[str], registry: dict[str, dict[str, Any]]) -> AsOf | None:
    """Declare the governing version when the question depends on time."""
    cue = bool(YEAR_CUE.search(question))
    policy_cited = any(
        (registry.get(doc_id) or {}).get("source_class") in ("normative", "standard")
        for doc_id in doc_ids
    )
    if not cue and not policy_cited:
        return None
    versions: list[VersionNote] = []
    for doc_id in dict.fromkeys(doc_ids):
        meta = registry.get(doc_id) or {}
        provenance = meta.get("provenance") or {}
        effective = meta.get("effective") or {}
        versions.append(
            VersionNote(
                doc_id=doc_id,
                document_no=str(provenance.get("document_no") or ""),
                effective=str(effective.get("from") or provenance.get("published_at") or ""),
                title=str(meta.get("title_zh") or meta.get("title") or ""),
            )
        )
    if not versions:
        return None
    first = versions[0]
    meta = registry.get(first.doc_id) or {}
    provenance = meta.get("provenance") or {}
    effective = meta.get("effective") or {}
    year = (
        str(meta.get("year") or "")
        or str(provenance.get("published_at") or "")[:4]
        or str(effective.get("from") or "")[:4]
    )
    label = first.document_no or first.title or first.doc_id
    declared = f"按{label}"
    effective_cn = _cn_date(first.effective)
    if first.document_no and effective_cn:
        declared += f"（{effective_cn}施行）"
    elif year.isdigit():
        declared += f"（{year}年版）"
    basis = "question_time_cue" if cue else "cited_policy"
    return AsOf(declared=declared, basis=basis, versions=tuple(versions[:1]))
