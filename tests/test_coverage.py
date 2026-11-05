from __future__ import annotations

from pathlib import Path

from scs_fkb.coverage import coverage_report, point_status
from scs_fkb.evaluate import load_anchors

ROOT = Path(__file__).resolve().parents[1]


def test_point_covered_by_cited_sentence() -> None:
    answer = "南海区休渔时间为5月1日12时至8月16日12时。 [POL-CLOS-015 §三]"
    covered, missing = point_status(
        answer,
        {"terms": ["5月1日", "8月16日"], "mode": "all"},
    )
    assert covered
    assert missing == []


def test_point_accepts_citation_after_newline() -> None:
    answer = "南海区休渔时间为5月1日12时至8月16日12时。\n[POL-CLOS-015 §三]"
    covered, _ = point_status(
        answer,
        {"terms": ["5月1日", "8月16日"], "mode": "all"},
    )
    assert covered


def test_point_requires_every_term() -> None:
    answer = "休渔时间为5月1日12时。 [POL-CLOS-015 §三]"
    covered, missing = point_status(
        answer,
        {"terms": ["5月1日", "8月16日"], "mode": "all"},
    )
    assert not covered
    assert missing == ["8月16日"]


def test_point_without_citation_is_not_covered() -> None:
    answer = "休渔时间为5月1日12时至8月16日12时。"
    covered, _ = point_status(
        answer,
        {"terms": ["5月1日", "8月16日"], "mode": "all"},
    )
    assert not covered


def test_any_mode() -> None:
    answer = "省级部门可以制定更严格标准。 [POL-GEAR-016 §四]"
    covered, _ = point_status(
        answer,
        {"terms": ["附件", "更严格"], "mode": "any"},
    )
    assert covered


def test_report_counts_points() -> None:
    gold = {"Q-E01": {"points": ["a", "b"]}}
    checks = {
        "Q-E01": [
            {"point": 0, "terms": ["a"], "mode": "all"},
            {"point": 1, "terms": ["b"], "mode": "all"},
        ]
    }
    results = [
        {
            "id": "Q-E01",
            "kind": "answerable",
            "answer": {"answer": "a。 [D §一]"},
        }
    ]
    report = coverage_report(gold, checks, results)
    assert report["summary"] == {"questions": 1, "points": 2, "covered": 1, "rate": 0.5}
    assert report["questions"]["Q-E01"]["missing"][0]["point"] == 1


def test_checks_cover_all_anchor_points() -> None:
    config = load_anchors(ROOT / "configs" / "eval.yaml")
    for question_id in config["anchors"]:
        points = config["gold"][question_id]["points"]
        checks = config["checks"][question_id]
        assert [item["point"] for item in checks] == list(range(len(points)))
        assert all(item.get("terms") for item in checks)


def test_section_mode_accepts_terms_across_sentences_same_section() -> None:
    answer = (
        "第一句给出条件甲 [POL-STD-010 §第四十一条]。\n第二句给出条件乙 [POL-STD-010 §第四十一条]。"
    )
    covered, missing = point_status(
        answer,
        {"terms": ["条件甲", "条件乙"], "mode": "section"},
    )
    assert covered
    assert missing == []


def test_section_mode_rejects_terms_from_different_sections() -> None:
    answer = (
        "第一句给出条件甲 [POL-STD-010 §第四十一条]。\n第二句给出条件乙 [POL-STD-010 §第四十二条]。"
    )
    covered, _ = point_status(
        answer,
        {"terms": ["条件甲", "条件乙"], "mode": "section"},
    )
    assert not covered


def test_section_mode_reports_missing_term() -> None:
    answer = "只给出条件甲。 [POL-STD-010 §第四十一条]"
    covered, missing = point_status(
        answer,
        {"terms": ["条件甲", "条件乙"], "mode": "section"},
    )
    assert not covered
    assert missing == ["条件乙"]


def test_nfkc_and_space_folding() -> None:
    answer = "每层不应少于 ３ 艘 [SC-T-9460 §5]。 "
    covered, _ = point_status(
        answer,
        {"terms": ["3艘"], "mode": "all"},
    )
    assert covered
