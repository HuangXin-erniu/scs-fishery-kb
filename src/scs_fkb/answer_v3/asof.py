from __future__ import annotations

import re
from typing import Any

from .contract import AsOf, VersionNote

YEAR_CUE = re.compile(r"今年|现在|目前|最新|当年|现行|本年度|当年|20\d{2}\s*年")


def detect(question: str, doc_ids: list[str], registry: dict[str, dict[str, Any]]) -> AsOf | None:
    """Declare the governing version when the question depends on time."""
    if not YEAR_CUE.search(question):
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
    if first.document_no and first.effective:
        declared += f"（{first.effective}施行）"
    elif year.isdigit():
        declared += f"（{year}年版）"
    return AsOf(declared=declared, basis="question_time_cue", versions=tuple(versions[:1]))
