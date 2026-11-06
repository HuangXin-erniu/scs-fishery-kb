from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.facts import load_all
from scs_fkb.knowledge_v2 import PlaybookError, check_playbooks, load_playbooks
from scs_fkb.terms import load_terms

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def _fact(status: str = "approved") -> dict:
    return {
        "id": "FACT-TEST-001",
        "kind": "atomic",
        "topic": "policy",
        "question_class": "definition",
        "subject": "测试对象",
        "predicate": "测试要点",
        "value": "测试值",
        "evidence": "测试证据",
        "source": {"doc": "POL-LAW-009", "section": "第一条", "sha256": HASH},
        "status": status,
        "confidence": "high",
        "as_of": "2026-11-06",
        "review_due": "2027-01-01",
        "jurisdiction": "national",
    }


def _playbook(fact_id: str = "FACT-TEST-001", **overrides) -> dict:
    playbook = {
        "id": "PLAY-CAPTAIN-901",
        "title": "测试流程",
        "persona": "captain",
        "applies_to": {"region": ["national"]},
        "steps": [
            {
                "order": 1,
                "action": "执行",
                "detail": "按依据执行。",
                "facts": [fact_id],
            }
        ],
        "sources": ["POL-LAW-009"],
        "status": "approved",
        "review_due": "2027-01-01",
    }
    playbook.update(overrides)
    return playbook


def _write_facts(tmp_path: Path, facts: list[dict]) -> Path:
    directory = tmp_path / "facts"
    directory.mkdir()
    (directory / "test.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "facts": facts}, allow_unicode=True),
        encoding="utf-8",
    )
    return directory


def _write_playbooks(tmp_path: Path, playbooks: list[dict]) -> Path:
    directory = tmp_path / "playbooks"
    directory.mkdir()
    (directory / "playbooks.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "playbooks": playbooks}, allow_unicode=True),
        encoding="utf-8",
    )
    return directory


def test_valid_playbook_passes(tmp_path: Path) -> None:
    result = check_playbooks(
        _write_playbooks(tmp_path, [_playbook()]),
        facts_dir=_write_facts(tmp_path, [_fact()]),
    )
    assert result.errors == []
    assert result.playbooks == 1
    assert result.steps == 1


def test_missing_fact_is_rejected(tmp_path: Path) -> None:
    result = check_playbooks(
        _write_playbooks(tmp_path, [_playbook("FACT-MISSING-999")]),
        facts_dir=_write_facts(tmp_path, [_fact()]),
    )
    assert any("unknown" in error for error in result.errors)


def test_draft_fact_is_rejected(tmp_path: Path) -> None:
    result = check_playbooks(
        _write_playbooks(tmp_path, [_playbook()]),
        facts_dir=_write_facts(tmp_path, [_fact(status="draft")]),
    )
    assert any("not approved" in error for error in result.errors)


def test_invalid_persona_is_rejected(tmp_path: Path) -> None:
    result = check_playbooks(
        _write_playbooks(tmp_path, [_playbook(persona="unknown")]),
        facts_dir=_write_facts(tmp_path, [_fact()]),
    )
    assert any("persona" in error for error in result.errors)


def test_duplicate_playbook_id_is_rejected(tmp_path: Path) -> None:
    path = _write_playbooks(tmp_path, [_playbook(), _playbook()])
    with pytest.raises(PlaybookError, match="duplicate"):
        load_playbooks(path)


def test_live_knowledge_counts() -> None:
    playbooks = load_playbooks(ROOT / "configs" / "playbooks")
    facts = load_all(ROOT / "configs" / "facts")
    terms = load_terms(ROOT / "configs" / "terms.yaml")
    assert len(playbooks) == 15
    assert len(facts) == 200
    assert len(terms) == 150
    result = check_playbooks(ROOT / "configs" / "playbooks")
    assert result.errors == []
    assert result.approved == 15
    promoted = {
        "FACT-PROV-025",
        "FACT-PROV-027",
        "FACT-PROV-033",
        "FACT-PROV-046",
        "FACT-PROV-060",
        "FACT-PROV-061",
        "FACT-PROV-063",
        "FACT-PROV-065",
        "FACT-PROV-066",
        "FACT-PROV-069",
        "FACT-PROV-076",
        "FACT-PROV-080",
        "FACT-PROV-081",
        "FACT-PROV-090",
        "FACT-PROV-095",
        "FACT-PROV-097",
        "FACT-PROV-098",
        "FACT-PROV-099",
        "FACT-PROV-100",
        "FACT-PROV-103",
    }
    by_id = {fact["id"]: fact for fact in facts}
    assert all(by_id[fid]["status"] == "approved" for fid in promoted)
    draft_terms = [term for term in terms if term["status"] == "draft"]
    assert len(draft_terms) == 27
    assert all(term["review"]["decision"] == "keep_draft" for term in draft_terms)
