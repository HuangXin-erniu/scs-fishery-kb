from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scs_fkb.ingest import knowledge_documents

SHA = "a" * 64


def _note(note_id: str, status: str = "approved", **overrides) -> dict:
    note = {
        "id": note_id,
        "title": "大黄鱼分类",
        "summary": "测试条目",
        "facts": [{"label": "学名", "value": "Larimichthys crocea"}],
        "as_of": "2026-11-03",
        "review_due": "2027-02-01",
        "status": status,
        "confidence": "high",
        "sources": [
            {
                "card": "WEB-TEST-001",
                "sha256": SHA,
                "url": "https://www.moa.gov.cn/x",
                "fetched_at": "2026-11-03",
            }
        ],
    }
    note.update(overrides)
    return note


def _setup(tmp_path: Path, notes: list[dict]) -> tuple[Path, Path]:
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "species.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": 1, "topic": "species", "notes": notes}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    cards = tmp_path / "web-cards.yaml"
    cards.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "cards": [
                    {
                        "id": "WEB-TEST-001",
                        "topic": "species",
                        "title": "t",
                        "publisher": "p",
                        "url": "https://www.moa.gov.cn/x",
                        "fetched_at": "2026-11-03",
                        "sha256": SHA,
                        "content_type": "text/html",
                        "license": "public",
                        "sensitivity": "public",
                        "source_class": "reference",
                        "file": "WEB-TEST-001/text.txt",
                        "status": "ok",
                        "excerpt": "x",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return knowledge, cards


def test_approved_notes_are_indexed(tmp_path: Path) -> None:
    knowledge, cards = _setup(tmp_path, [_note("KNO-SPECIES-001")])
    documents, chunks, entries, counts = knowledge_documents(
        knowledge, cards, 400, today=date(2026, 11, 3)
    )
    assert [doc.doc_id for doc in documents] == ["KNO-SPECIES-001"]
    assert chunks and chunks[0].url == "https://www.moa.gov.cn/x"
    assert chunks[0].retrieved_at == "2026-11-03"
    assert entries[0]["kind"] == "knowledge_note"
    assert counts["KNO-SPECIES-001"] == len(chunks)


def test_draft_and_stale_notes_are_skipped(tmp_path: Path) -> None:
    notes = [_note("KNO-SPECIES-001", status="draft"), _note("KNO-SPECIES-002")]
    knowledge, cards = _setup(tmp_path, notes)
    # change the card hash so note 002 is stale
    data = yaml.safe_load(cards.read_text(encoding="utf-8"))
    data["cards"][0]["sha256"] = "b" * 64
    cards.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    documents, _, _, _ = knowledge_documents(knowledge, cards, 400, today=date(2026, 11, 3))
    assert documents == []


def test_expired_hazard_is_skipped(tmp_path: Path) -> None:
    note = _note("KNO-HAZARD-001", topic="hazard", expires_at="2026-11-01")
    note["sources"] = [{"doc": "POL-TEST", "sha256": "c" * 64}]
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "hazard.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": 1, "topic": "hazard", "notes": [note]}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    cards = tmp_path / "web-cards.yaml"
    cards.write_text(yaml.safe_dump({"schema_version": 1, "cards": []}), encoding="utf-8")
    documents, _, _, _ = knowledge_documents(knowledge, cards, 400, today=date(2026, 11, 3))
    assert documents == []
