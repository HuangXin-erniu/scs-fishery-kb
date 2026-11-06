from __future__ import annotations

from pathlib import Path

from scs_fkb.facts import fact_documents
from scs_fkb.faq import faq_documents
from scs_fkb.terms import term_documents

ROOT = Path(__file__).resolve().parents[1]


def test_fact_term_faq_builders_add_expected_documents() -> None:
    fact_docs, fact_chunks, _fact_entries, fact_counts = fact_documents(
        ROOT / "configs" / "facts",
        data_root=ROOT,
        registry_path=ROOT / "configs" / "corpus.yaml",
    )
    term_docs, term_chunks, _term_entries, term_counts = term_documents(
        ROOT / "configs" / "terms.yaml"
    )
    faq_docs, faq_chunks, _faq_entries, faq_counts = faq_documents(ROOT / "configs" / "faq.yaml")
    assert len(fact_docs) == 100
    assert len(fact_chunks) == 100
    assert sum(fact_counts.values()) == 100
    assert len(term_docs) == 123
    assert len(term_chunks) == 123
    assert sum(term_counts.values()) == 123
    assert len(faq_docs) == 12
    assert len(faq_chunks) == 12
    assert sum(faq_counts.values()) == 12
