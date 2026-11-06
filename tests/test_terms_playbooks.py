from __future__ import annotations

from scs_fkb.terms import load_terms


def test_terms_are_unique_and_complete() -> None:
    terms = load_terms("configs/terms.yaml")
    assert len(terms) == 150
    assert len({term["standard"] for term in terms}) == 150
    assert len({term["id"] for term in terms}) == 150
    approved = [term for term in terms if term.get("status") == "approved"]
    draft = [term for term in terms if term.get("status") == "draft"]
    assert len(approved) >= 24
    assert len(approved) + len(draft) == 150
