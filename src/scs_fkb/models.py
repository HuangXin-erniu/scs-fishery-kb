from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    id: str
    category: str
    title: str
    title_zh: str
    publisher: str
    year: int | None
    doc_type: str
    format: str
    location: str
    license: str
    sensitivity: str
    status: str
    hash: str


@dataclass(frozen=True)
class Document:
    doc_id: str
    source_id: str
    title: str
    title_zh: str
    publisher: str
    year: int | None
    doc_type: str
    sensitivity: str
    language: str
    page_count: int
    file_hash: str
    version_id: str = ""
    snapshot_hash: str = ""
    authority_tier: str = ""
    level: str = ""
    source_class: str = ""
    license: str = ""
    jurisdiction: str = ""
    effective_from: str = ""
    effective_to: str = ""
    url: str = ""
    retrieved_at: str = ""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    source_id: str
    page: int
    section: str
    text: str
    token_count: int
    char_start: int
    char_end: int
    sensitivity: str
    url: str = ""
    retrieved_at: str = ""
    kind: str = "corpus"
    source_class: str = ""
    trust: str = ""
    review_due: str = ""
    parent_id: str = ""
    chunk_type: str = "text"
    section_path: str = ""
    version_id: str = ""
    snapshot_hash: str = ""
    authority_tier: str = ""
    level: str = ""
    jurisdiction: str = ""
    license: str = ""
    effective_from: str = ""
    effective_to: str = ""


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "page": self.chunk.page,
            "section": self.chunk.section,
            "score": round(self.score, 6),
            "text": self.chunk.text,
        }


@dataclass(frozen=True)
class Citation:
    doc_id: str
    title: str
    page: int
    section: str
    snippet: str
    score: float
    url: str = ""
    retrieved_at: str = ""


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    abstained: bool = False
    reason: str = "ok"
    # Structured clauses for the summary selector; never serialized and never
    # part of the evidence text, so the acceptance run sees the same answer.
    clauses: tuple[Any, ...] = ()

    def to_dict(self) -> dict:
        return {
            "answer": self.text,
            "citations": [
                {
                    "doc_id": citation.doc_id,
                    "title": citation.title,
                    "page": citation.page,
                    "section": citation.section,
                    "snippet": citation.snippet,
                    "score": round(citation.score, 6),
                }
                for citation in self.citations
            ],
            "abstained": self.abstained,
            "reason": self.reason,
        }
