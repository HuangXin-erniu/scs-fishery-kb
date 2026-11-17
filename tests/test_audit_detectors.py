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


def test_d9_ignores_asof_metadata_year() -> None:
    from scs_fkb.audit.detectors import d9

    record = AuditRecord(
        id="D9-ASOF",
        source="canary",
        question="休渔时间？",
        visible_answer=(
            "休渔时间为5月1日12时 [POL-A-001 §一]。\n"
            "时效：本答复依据《某规定》（2025年）；以最新公布为准。"
        ),
        citations=[{"doc_id": "POL-A-001", "section": "一"}],
        evidence_ids=["POL-A-001"],
    )
    assert d9(record, [("一", "休渔时间为5月1日12时")]) == []


def test_d11_accepts_four_digit_year_without_the_character() -> None:
    from scs_fkb.audit.detectors import d11

    record = AuditRecord(
        id="D11-YEAR",
        source="canary",
        question="休渔时间？",
        visible_answer="休渔时间为5月1日12时 [POL-A-001 §一]；依据2021。",
        citations=[{"doc_id": "POL-A-001", "section": "一"}],
        evidence_ids=["POL-A-001"],
    )
    assert d11(record, {"POL-A-001": {"year": 2021}}) == []
