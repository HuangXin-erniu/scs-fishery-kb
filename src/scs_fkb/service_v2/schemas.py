from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Persona = Literal["captain", "owner", "enforcement", "extension", "general"]
Mode = Literal["kb_only", "clarify", "abstain"]
Answerability = Literal["answerable", "partial", "abstain"]


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    persona: Persona = "general"
    region: str | None = Field(default=None, max_length=32)
    year: int | None = Field(default=None, ge=1949, le=2100)


class CitationModel(BaseModel):
    doc_id: str
    title: str
    page: int | None = None
    section: str | None = None
    snippet: str
    score: float = 0.0
    url: str = ""
    retrieved_at: str = ""
    source_type: Literal["corpus"] = "corpus"
    label: str = ""


class PlaybookStep(BaseModel):
    order: int
    action: str
    detail: str
    facts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class PlaybookView(BaseModel):
    id: str
    title: str
    persona: str
    steps: list[PlaybookStep] = Field(default_factory=list)


class VersionModel(BaseModel):
    doc_id: str
    document_no: str = ""
    effective: str = ""
    title: str = ""


class AsOfModel(BaseModel):
    declared: str
    basis: str = ""
    versions: list[VersionModel] = Field(default_factory=list)


class NumericModel(BaseModel):
    value: str
    unit: str = ""
    basis: str = ""
    location: str = ""


class ChannelModel(BaseModel):
    name: str
    hint: str = ""
    doc_id: str = ""


class QueryResponse(BaseModel):
    request_id: str
    answer: str
    summary: str = ""
    citations_total: int = 0
    citations: list[CitationModel] = Field(default_factory=list)
    abstained: bool = False
    reason: str = "ok"
    mode: Mode = "kb_only"
    playbook: PlaybookView | None = None
    index_version: str = "v2"
    answerability: Answerability = "answerable"
    conclusion: str = ""
    conditions: list[str] = Field(default_factory=list)
    gap: list[str] = Field(default_factory=list)
    channel: list[ChannelModel] = Field(default_factory=list)
    as_of: AsOfModel | None = None
    numbers: list[NumericModel] = Field(default_factory=list)
    latency_ms: int = 0
    disclaimer: str = "以官方发布文本为准；本服务不构成法律意见。"


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    helpful: bool
    comment: str = Field(default="", max_length=1000)
    question: str = Field(default="", max_length=500)


class SourceView(BaseModel):
    id: str
    title: str
    publisher: str
    tier: str
    year: int | None = None
    url: str = ""


class HealthResponse(BaseModel):
    status: str
    index_version: str = "v2"
