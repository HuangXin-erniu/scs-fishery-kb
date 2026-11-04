from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scs_fkb.evaluate import (
    _answer_quality,
    anchor_matches,
    group_summary,
    load_anchors,
    parse_questions,
    summarize,
    summarize_jurisdiction,
    summarize_national,
)
from scs_fkb.models import Answer, Chunk

TABLE = """# Questions

| ID | Question (English) | Original (Chinese) | Type | Expected evidence | Notes |
|---|---|---|---|---|---|
| Q-E01 | Closure dates? | 南海区伏季休渔的起止日期是什么？ | policy | POL-LAW-009 | x |
| Q-E07 | Fishing season? | 某渔场的历史渔汛期是什么？ | fact | none registered | x |
"""

ANCHORS = """schema_version: 1
anchors:
  Q-E01:
    - {doc: POL-LAW-009, section: "第四十四条"}
  Q-E10:
    - {doc: POL-GEAR-033}
abstention:
  - Q-E07
"""


def _chunk(doc: str = "POL-LAW-009", page: int = 0, section: str = "第四十四条") -> Chunk:
    return Chunk(
        chunk_id=f"{doc}-0000",
        doc_id=doc,
        source_id=doc,
        page=page,
        section=section,
        text="text",
        token_count=1,
        char_start=0,
        char_end=4,
        sensitivity="public",
    )


def test_parse_questions(tmp_path: Path) -> None:
    path = tmp_path / "questions.md"
    path.write_text(TABLE, encoding="utf-8")
    rows = parse_questions(path)
    assert [row["id"] for row in rows] == ["Q-E01", "Q-E07"]
    assert rows[0]["question"].startswith("南海区")


def test_load_anchors(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(ANCHORS, encoding="utf-8")
    config = load_anchors(path)
    assert list(config["anchors"]) == ["Q-E01", "Q-E10"]
    assert config["abstention"] == ["Q-E07"]


def test_parse_questions_accepts_persona_ids(tmp_path: Path) -> None:
    path = tmp_path / "questions.md"
    path.write_text(TABLE.replace("| Q-E01 |", "| Q-C01 |"), encoding="utf-8")
    assert [row["id"] for row in parse_questions(path)] == ["Q-C01", "Q-E07"]


def test_load_anchors_reads_meta(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        ANCHORS
        + "meta:\n"
        + "  Q-E01: {persona: captain, split: dev}\n"
        + "  Q-E07: {persona: captain, split: dev}\n"
        + "  Q-E10: {persona: extension, split: test}\n",
        encoding="utf-8",
    )
    config = load_anchors(path)
    assert config["meta"]["Q-E10"] == {"persona": "extension", "split": "test"}


def test_load_anchors_rejects_bad_persona(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        ANCHORS + "meta:\n  Q-E01: {persona: skipper, split: dev}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="persona"):
        load_anchors(path)


def test_load_anchors_rejects_bad_split(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        ANCHORS + "meta:\n  Q-E01: {persona: captain, split: validation}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="split"):
        load_anchors(path)


def test_load_anchors_rejects_empty_entries(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text("schema_version: 1\nanchors:\n  Q-E01: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no anchors"):
        load_anchors(path)


def test_anchor_matches_section_prefix() -> None:
    assert anchor_matches(_chunk(), {"doc": "POL-LAW-009", "section": "第四十四条"})
    assert anchor_matches(_chunk(), {"doc": "POL-LAW-009", "section": "第四十"})
    assert not anchor_matches(_chunk(), {"doc": "POL-LAW-009", "section": "第四十五条"})
    assert not anchor_matches(_chunk(), {"doc": "POL-STD-010", "section": "第四十四条"})


def test_anchor_matches_page() -> None:
    chunk = _chunk(doc="POL-PLAN-038", page=9, section="")
    assert anchor_matches(chunk, {"doc": "POL-PLAN-038", "page": 9})
    assert not anchor_matches(chunk, {"doc": "POL-PLAN-038", "page": 10})


def test_anchor_matches_document_only() -> None:
    chunk = _chunk(doc="POL-GEAR-033", page=0, section="")
    assert anchor_matches(chunk, {"doc": "POL-GEAR-033"})
    assert not anchor_matches(chunk, {"doc": "POL-GEAR-034"})


def test_summarize_counts() -> None:
    results = [
        {"kind": "answerable", "hit": True, "abstained": False, "citation_valid": True},
        {"kind": "answerable", "hit": True, "abstained": True, "citation_valid": True},
        {"kind": "answerable", "hit": False, "abstained": False, "citation_valid": True},
        {"kind": "abstention", "hit": None, "abstained": True, "citation_valid": True},
        {"kind": "abstention", "hit": None, "abstained": False, "citation_valid": True},
    ]
    summary = summarize(results, ["Q-E05"])
    assert summary["answerable_questions"] == 3
    assert summary["abstention_tests"] == 2
    assert summary["recall_hits"] == 2
    assert summary["recall_at_5"] == 0.6667
    assert summary["abstention_rate"] == 0.5
    assert summary["false_refusals"] == 1
    assert summary["skipped_questions"] == 1
    assert summary["citation_resolution"] == 1.0
    assert summary["answer_rate"] == 0.6667
    assert summary["citation_coverage"] == 0.0
    assert summary["faithfulness"] == 0.0


def test_group_summary_splits_and_personas() -> None:
    results = [
        {
            "kind": "answerable",
            "hit": True,
            "abstained": False,
            "citation_valid": True,
            "split": "dev",
            "persona": "captain",
        },
        {
            "kind": "abstention",
            "hit": None,
            "abstained": True,
            "citation_valid": True,
            "split": "test",
            "persona": "owner",
        },
        {
            "kind": "answerable",
            "hit": False,
            "abstained": True,
            "citation_valid": True,
            "split": "test",
            "persona": "owner",
        },
    ]
    by_split = group_summary(results, "split", ("dev", "test"))
    assert by_split["dev"]["answerable_questions"] == 1
    assert by_split["test"]["answerable_questions"] == 1
    assert by_split["test"]["abstention_tests"] == 1
    by_persona = group_summary(results, "persona", ("captain", "owner"))
    assert by_persona["captain"]["answerable_questions"] == 1
    assert by_persona["owner"]["answerable_questions"] == 1
    assert by_persona["owner"]["abstention_tests"] == 1


def test_answer_quality_supported_and_unsupported() -> None:
    hit = SimpleNamespace(chunk=_chunk())
    supported = Answer(text="text [POL-LAW-009 §第四十四条]", citations=[])
    assert _answer_quality(supported, [hit]) == {
        "citation_coverage": 1.0,
        "faithful": True,
        "sentences": 1,
    }
    unsupported = Answer(text="not in the chunk [POL-LAW-009 §第四十四条]", citations=[])
    assert _answer_quality(unsupported, [hit])["faithful"] is False


def test_load_anchors_rejects_malformed_reference(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        "schema_version: 1\nanchors:\n  Q-E01:\n    - {doc: POL-LAW-009}\n"
        "reference:\n  - {id: Q-E05}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed reference"):
        load_anchors(path)


def test_summarize_reference() -> None:
    from scs_fkb.evaluate import summarize_reference

    rows = [{"hit": True}, {"hit": False}]
    summary = summarize_reference(rows)
    assert summary["reference_questions"] == 2
    assert summary["reference_hits"] == 1
    assert summary["reference_rate"] == 0.5
    assert summarize_reference([])["reference_rate"] == 0.0


def test_load_anchors_accepts_statistics(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        "schema_version: 1\n"
        "anchors:\n  Q-E01:\n    - {doc: POL-LAW-009}\n"
        "statistics:\n"
        "  - {id: Q-E06, query: 南海区海洋捕捞产量, expect: capture_production_sea_area}\n",
        encoding="utf-8",
    )
    config = load_anchors(path)
    assert [item["id"] for item in config["statistics"]] == ["Q-E06"]


def test_load_anchors_rejects_malformed_statistics(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(
        "schema_version: 1\nanchors:\n  Q-E01:\n    - {doc: POL-LAW-009}\n"
        "statistics:\n  - {id: Q-E06}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed statistics"):
        load_anchors(path)


def test_summarize_statistics() -> None:
    from scs_fkb.evaluate import summarize_statistics

    rows = [
        {"hit": True, "skipped": False},
        {"hit": False, "skipped": False},
        {"hit": False, "skipped": True},
    ]
    summary = summarize_statistics(rows)
    assert summary["statistics_questions"] == 3
    assert summary["statistics_hits"] == 1
    assert summary["statistics_skipped"] == 1
    assert summarize_statistics([])["statistics_rate"] == 0.0


JURISDICTION = (
    ANCHORS
    + """
jurisdiction:
  - id: J1
    query: 海南省休渔时间是什么？
    docs: [POL-HN-059]
"""
)


def test_load_anchors_reads_the_jurisdiction_section(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(JURISDICTION, encoding="utf-8")
    config = load_anchors(path)
    assert config["jurisdiction"][0]["id"] == "J1"
    assert config["jurisdiction"][0]["docs"] == ["POL-HN-059"]


def test_malformed_jurisdiction_entry_raises(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(ANCHORS + "\njurisdiction:\n  - id: J1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="jurisdiction"):
        load_anchors(path)


def test_summarize_jurisdiction_counts_hits() -> None:
    summary = summarize_jurisdiction([{"hit": True}, {"hit": False}, {"hit": True}])
    assert summary["jurisdiction_questions"] == 3
    assert summary["jurisdiction_hits"] == 2
    assert summary["jurisdiction_rate"] == pytest.approx(0.6667, abs=0.0001)


NATIONAL = (
    ANCHORS
    + """
national:
  - id: J4
    query: 2026年海洋伏季休渔执法行动的重点任务是什么？
    docs: [POL-ENF-068]
"""
)


def test_load_anchors_reads_the_national_section(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(NATIONAL, encoding="utf-8")
    config = load_anchors(path)
    assert config["national"][0]["id"] == "J4"
    assert config["national"][0]["docs"] == ["POL-ENF-068"]


def test_malformed_national_entry_raises(tmp_path: Path) -> None:
    path = tmp_path / "eval.yaml"
    path.write_text(ANCHORS + "\nnational:\n  - id: J4\n", encoding="utf-8")
    with pytest.raises(ValueError, match="national"):
        load_anchors(path)


def test_summarize_national_counts_hits() -> None:
    summary = summarize_national([{"hit": True}, {"hit": True}])
    assert summary["national_questions"] == 2
    assert summary["national_hits"] == 2
    assert summary["national_rate"] == 1.0
