from __future__ import annotations

import json
from pathlib import Path

import pytest

from scs_fkb.audit.detectors import d1, d2, d3, d4
from scs_fkb.audit.schema import AuditRecord

FIXTURE = Path(__file__).parent / "fixtures" / "audit" / "canary_d1_d4.jsonl"


def _record(case: dict) -> AuditRecord:
    return AuditRecord(
        id=case["id"],
        source="canary",
        question=case["question"],
        visible_answer=case["answer"],
        evidence_ids=[],
    )


@pytest.mark.parametrize(
    "case",
    [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()],
)
def test_d1_d4_canary(case: dict) -> None:
    record = _record(case)
    chunks = [("canary", text) for text in case.get("chunks", [])]
    detector = case["detector"]
    findings = {
        "D1": lambda: d1(record, chunks),
        "D2": lambda: d2(record),
        "D3": lambda: d3(record),
        "D4": lambda: d4(record),
    }[detector]()
    assert bool(findings) is case["should_flag"], (case["id"], findings)
