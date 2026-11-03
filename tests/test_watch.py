from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scs_fkb.watch import due_report


def _write(
    tmp_path: Path, corpus: dict, cards: list[dict], topics: dict
) -> tuple[Path, Path, Path]:
    registry = tmp_path / "corpus.yaml"
    registry.write_text(yaml.safe_dump(corpus, allow_unicode=True), encoding="utf-8")
    cards_path = tmp_path / "web-cards.yaml"
    cards_path.write_text(
        yaml.safe_dump({"schema_version": 1, "cards": cards}, allow_unicode=True), encoding="utf-8"
    )
    sources = tmp_path / "web-sources.yaml"
    sources.write_text(
        yaml.safe_dump({"schema_version": 1, "topics": topics}, allow_unicode=True),
        encoding="utf-8",
    )
    return registry, cards_path, sources


def _entry(source_id: str, due: str) -> dict:
    return {
        "id": source_id,
        "level": "national",
        "authority_tier": "A",
        "source_class": "normative",
        "currency": {"as_of": "2026-11-01", "basis": "publication", "review_due": due},
        "retrieval": {"channel": "collection", "parseable": True, "note": "x"},
        "lifecycle": "active",
    }


def test_corpus_entries_due_and_not_due(tmp_path: Path) -> None:
    corpus = {"sources": [_entry("A", "2026-11-02"), _entry("B", "2026-11-04")]}
    registry, cards_path, sources = _write(tmp_path, corpus, [], {"species": {"cadence_days": 30}})
    report = due_report(registry, cards_path, sources, today=date(2026, 11, 3))
    assert [row["id"] for row in report["corpus"]] == ["A"]
    assert report["cards"] == []


def test_cards_due_by_cadence_and_failed_excluded(tmp_path: Path) -> None:
    corpus = {"sources": [_entry("A", "2026-12-01")]}
    cards = [
        {
            "id": "WEB-OLD",
            "topic": "species",
            "status": "ok",
            "fetched_at": "2026-10-01T00:00:00+00:00",
        },
        {
            "id": "WEB-NEW",
            "topic": "species",
            "status": "ok",
            "fetched_at": "2026-11-02T00:00:00+00:00",
        },
        {
            "id": "WEB-BAD",
            "topic": "species",
            "status": "failed",
            "fetched_at": "2026-01-01T00:00:00+00:00",
        },
    ]
    registry, cards_path, sources = _write(
        tmp_path, corpus, cards, {"species": {"cadence_days": 30}}
    )
    report = due_report(registry, cards_path, sources, today=date(2026, 11, 3))
    assert [row["id"] for row in report["cards"]] == ["WEB-OLD"]
