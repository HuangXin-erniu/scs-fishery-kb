from __future__ import annotations

import json
from pathlib import Path

import pytest

from scs_fkb.audit.detectors import d5, d6, d7, d8, d9, d10, d11
from scs_fkb.audit.normalize import citations
from scs_fkb.audit.schema import AuditRecord

FIXTURE = Path(__file__).parent / "fixtures" / "audit" / "canary_d5_d11.jsonl"


def _record(case: dict) -> AuditRecord:
    return AuditRecord(
        id=case["id"],
        source="canary",
        question=case["question"],
        visible_answer=case["answer"],
        citations=[
            {"doc_id": doc, "section": section} for doc, section in citations(case["answer"])
        ],
        abstained=case["abstained"],
    )


@pytest.mark.parametrize(
    "case",
    [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()],
)
def test_d5_d11_canary(case: dict) -> None:
    record = _record(case)
    chunks = [("一", text) for text in case.get("chunks", [])]
    chunk_index = {"POL-X": chunks} if chunks else {}
    doc_meta = case.get("doc_meta", {})
    detector = case["detector"]
    findings = {
        "D5": lambda: d5(record, chunks),
        "D6": lambda: d6(record),
        "D7": lambda: d7(record, chunk_index),
        "D8": lambda: d8(record, doc_meta),
        "D9": lambda: d9(record, chunks),
        "D10": lambda: d10(record),
        "D11": lambda: d11(record, doc_meta),
    }[detector]()
    assert bool(findings) is case["should_flag"], (case["id"], findings)
