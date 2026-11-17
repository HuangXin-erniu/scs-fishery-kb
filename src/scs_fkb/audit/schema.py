from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditRecord:
    id: str
    source: str
    question: str
    visible_answer: str
    citations: list[dict[str, str]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    abstained: bool = False
    reason: str = ""
    pipeline_stage: str = "compose"
    reference: str = ""
    theme: str = "其他"
    gap_status: str = ""
    trace_ref: str = ""
    index_version: str = ""
    commit: str = ""
    answer_kind: str = "delivery"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "question": self.question,
            "visible_answer": self.visible_answer,
            "citations": self.citations,
            "evidence_ids": sorted(set(self.evidence_ids)),
            "abstained": self.abstained,
            "reason": self.reason,
            "pipeline_stage": self.pipeline_stage,
            "reference": self.reference,
            "theme": self.theme,
            "gap_status": self.gap_status,
            "trace_ref": self.trace_ref,
            "index_version": self.index_version,
            "commit": self.commit,
            "answer_kind": self.answer_kind,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Finding:
    id: str
    detector: str
    severity: str
    sentence: str
    evidence_pointer: str = ""
    chunk_id: str = ""
    rule_version: str = "v1"

    def to_row(self) -> dict[str, str]:
        return {
            "id": self.id,
            "detector": self.detector,
            "severity": self.severity,
            "sentence": self.sentence,
            "evidence_pointer": self.evidence_pointer,
            "chunk_id": self.chunk_id,
            "rule_version": self.rule_version,
        }


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[AuditRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
