from __future__ import annotations

import json
from pathlib import Path

from scs_fkb.claims import record_gap


def test_gap_is_appended_with_fields(tmp_path: Path) -> None:
    path = tmp_path / "gaps.jsonl"
    record_gap(path, "某问题？", "weak_evidence", "definition", "policy")
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["question"] == "某问题？"
    assert row["reason"] == "weak_evidence"
    assert row["nature"] == "definition"
    assert row["domain"] == "policy"
    assert row["ts"]


def test_gap_creates_parent_and_appends(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "gaps.jsonl"
    record_gap(path, "第一问", "no_evidence", "general", "general")
    record_gap(path, "第二问", "no_corpus_evidence", "status", "policy")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["question"] == "第二问"


def test_gap_summary_counts_and_recent(tmp_path: Path) -> None:
    from scs_fkb.claims import summarize_gaps

    path = tmp_path / "gaps.jsonl"
    record_gap(path, "第一问", "weak_evidence", "status", "policy")
    record_gap(path, "第二问", "no_evidence", "definition", "policy")
    record_gap(path, "第三问", "weak_evidence", "status", "gear")
    report = summarize_gaps(path)
    assert report["total"] == 3
    assert report["by_nature"]["status"] == 2
    assert report["by_domain"]["policy"] == 2
    assert report["by_reason"]["weak_evidence"] == 2
    assert report["recent"][-1] == "第三问"


def test_gap_summary_handles_missing_file(tmp_path: Path) -> None:
    from scs_fkb.claims import summarize_gaps

    report = summarize_gaps(tmp_path / "absent.jsonl")
    assert report["total"] == 0
    assert report["by_nature"] == {}
