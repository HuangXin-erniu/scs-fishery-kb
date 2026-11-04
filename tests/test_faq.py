from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scs_fkb.faq import FaqError, check_faqs, load_faqs, validate_faq


def _fact(fact_id: str = "FACT-POLICY-001", status: str = "approved") -> dict:
    return {
        "id": fact_id,
        "kind": "atomic",
        "topic": "policy",
        "question_class": "penalty",
        "subject": "测试",
        "predicate": "罚款",
        "value": "1000元",
        "evidence": "处1000元罚款",
        "source": {"doc": "POL-TEST-001", "sha256": "a" * 64},
        "status": status,
        "confidence": "high",
        "as_of": "2026-11-04",
        "review_due": "2026-12-03",
    }


def _facts(tmp_path: Path, facts: list[dict]) -> Path:
    path = tmp_path / "facts" / "policy.yaml"
    path.parent.mkdir()
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "topic": "policy", "facts": facts}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    return path.parent


def _faq(**overrides) -> dict:
    item = {
        "id": "FAQ-CAPTAIN-001",
        "question": "罚款多少？",
        "persona": "captain",
        "claims": ["FACT-POLICY-001"],
        "source": {"kind": "public", "note": "test"},
        "status": "approved",
    }
    item.update(overrides)
    return item


def _write(tmp_path: Path, faqs: list[dict]) -> Path:
    path = tmp_path / "faq.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "faqs": faqs}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_valid_faq_passes_check(tmp_path: Path) -> None:
    report = check_faqs(_write(tmp_path, [_faq()]), facts_dir=_facts(tmp_path, [_fact()]))
    assert report["errors"] == []
    assert report["approved"] == 1


def test_unknown_claim_fails_check(tmp_path: Path) -> None:
    report = check_faqs(
        _write(tmp_path, [_faq(claims=["FACT-MISSING-001"])]),
        facts_dir=_facts(tmp_path, [_fact()]),
    )
    assert any("is not a fact" in error for error in report["errors"])


def test_approved_faq_cannot_claim_draft_fact(tmp_path: Path) -> None:
    report = check_faqs(
        _write(tmp_path, [_faq()]),
        facts_dir=_facts(tmp_path, [_fact(status="draft")]),
    )
    assert any("non-approved fact" in error for error in report["errors"])


def test_empty_claims_are_rejected() -> None:
    assert any("claims" in error for error in validate_faq(_faq(claims=[])))


def test_duplicate_question_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FaqError, match="duplicate question"):
        load_faqs(_write(tmp_path, [_faq(), _faq(id="FAQ-CAPTAIN-002")]))


def test_real_faq_layer_has_12_items() -> None:
    root = Path(__file__).resolve().parents[1]
    faqs = load_faqs(root / "configs" / "faq.yaml")
    assert len(faqs) == 12
    assert all(faq["claims"] for faq in faqs)


def test_real_faq_extension_claims_point_at_gear_facts() -> None:
    root = Path(__file__).resolve().parents[1]
    faqs = {faq["id"]: faq for faq in load_faqs(root / "configs" / "faq.yaml")}
    assert faqs["FAQ-EXTENSION-001"]["claims"] == ["FACT-GEAR-001"]
    assert faqs["FAQ-EXTENSION-002"]["claims"] == ["FACT-GEAR-002"]
    assert faqs["FAQ-EXTENSION-003"]["claims"] == ["FACT-GEAR-003"]
