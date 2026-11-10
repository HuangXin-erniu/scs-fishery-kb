from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from scs_fkb.kb_v2 import build_numbers, build_updates, load_faq, load_terms_plain


def test_load_faq_rejects_a_bad_entry(tmp_path: Path) -> None:
    path = tmp_path / "faq.yaml"
    path.write_text(
        yaml.safe_dump({"entries": [{"id": "FAQ-1", "question": "q"}]}, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="bad FAQ id"):
        load_faq(path)


def test_load_terms_plain_rejects_a_duplicate(tmp_path: Path) -> None:
    row = {
        "term_id": "TERM-001",
        "official": "渔业捕捞许可证",
        "plain": "捕鱼用的证",
        "citations": [{"doc": "POL-STD-010", "section": "第二条"}],
    }
    path = tmp_path / "terms.yaml"
    path.write_text(yaml.safe_dump({"terms": [row, row]}, allow_unicode=True), encoding="utf-8")
    with pytest.raises(Exception, match="duplicate"):
        load_terms_plain(path)


def test_build_numbers_keeps_only_approved_numeric_facts() -> None:
    facts = [
        {
            "id": "F1",
            "status": "approved",
            "value": "5月1日12时",
            "unit": "None",
            "topic": "policy",
            "subject": "休渔",
            "predicate": "开始",
            "source": {"doc": "POL-CLOS-015", "section": "三、休渔时间"},
            "review_due": "2026-12-03",
        },
        {
            "id": "F2",
            "status": "approved",
            "value": "除钓具外的所有作业类型",
            "unit": None,
            "topic": "policy",
            "subject": "休渔",
            "predicate": "类型",
            "source": {"doc": "POL-CLOS-015", "section": "二、休渔作业类型"},
        },
        {
            "id": "F3",
            "status": "draft",
            "value": "1000元",
            "source": {"doc": "POL-PEN-080", "section": "第八条"},
        },
    ]
    rows = build_numbers(facts)
    assert [row["value"] for row in rows] == ["5月1日12时"]
    assert rows[0]["unit"] == ""


def test_build_updates_from_registry() -> None:
    registry = {
        "POL-1": {
            "lifecycle": "active",
            "title": "通告",
            "authority_tier": "A",
            "currency": {"as_of": "2026-11-01", "review_due": "2026-12-01"},
            "supersedes": "POL-0",
        }
    }
    updates = build_updates(registry, today=date(2026, 11, 10))
    assert updates["recent"][0]["id"] == "POL-1"
    assert updates["upcoming"][0]["review_due"] == "2026-12-01"
    assert updates["superseded"][0]["supersedes"] == "POL-0"
