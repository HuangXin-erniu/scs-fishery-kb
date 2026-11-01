from __future__ import annotations

from pathlib import Path

from scs_fkb.evaluate import parse_questions, select_questions, summarize

TABLE = """# Questions

| ID | Question (English) | Original (Chinese) | Type | Expected evidence | Notes |
|---|---|---|---|---|---|
| Q-E01 | Closure dates? | 南海区伏季休渔的起止日期是什么？ | policy | POL-LAW-009 | x |
| Q-E07 | Fishing season? | 某渔场的历史渔汛期是什么？ | fact | none registered | x |
| Q-E10 | Gear standard? | 某类渔具的现行标准是什么？ | standard | POL-GEAR-033 / POL-GEAR-034 | x |
"""


def _questions(tmp_path: Path) -> Path:
    path = tmp_path / "questions.md"
    path.write_text(TABLE, encoding="utf-8")
    return path


def test_parse_questions(tmp_path: Path) -> None:
    rows = parse_questions(_questions(tmp_path))
    assert [row["id"] for row in rows] == ["Q-E01", "Q-E07", "Q-E10"]
    assert rows[0]["question"].startswith("南海区")
    assert rows[0]["evidence_ids"] == ["POL-LAW-009"]
    assert rows[1]["evidence_ids"] == []
    assert rows[2]["evidence_ids"] == ["POL-GEAR-033", "POL-GEAR-034"]


def test_select_questions(tmp_path: Path) -> None:
    rows = parse_questions(_questions(tmp_path))
    m1, abstention, skipped = select_questions(rows, ["POL-LAW-009", "POL-STD-010"])
    assert [row["id"] for row in m1] == ["Q-E01"]
    assert [row["id"] for row in abstention] == ["Q-E07"]
    assert [row["id"] for row in skipped] == ["Q-E10"]


def test_summarize() -> None:
    results = [
        {"kind": "answerable", "retrieved": True, "abstained": False, "citation_valid": True},
        {"kind": "answerable", "retrieved": True, "abstained": True, "citation_valid": True},
        {"kind": "answerable", "retrieved": True, "abstained": False, "citation_valid": True},
        {"kind": "abstention", "retrieved": None, "abstained": True, "citation_valid": True},
        {"kind": "abstention", "retrieved": None, "abstained": False, "citation_valid": True},
    ]
    summary = summarize(results)
    assert summary["answerable_questions"] == 3
    assert summary["abstention_tests"] == 2
    assert summary["recall_at_5"] == 1.0
    assert summary["abstention_rate"] == 0.5
    assert summary["false_refusals"] == 1
    assert summary["citation_resolution"] == 1.0
