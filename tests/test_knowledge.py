from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from scs_fkb.knowledge import (
    KnowledgeError,
    approve,
    check,
    list_notes,
    load_knowledge,
)

CARD_SHA = "a" * 64


def _note(note_id: str = "KNO-SPECIES-001", **overrides) -> dict:
    note = {
        "id": note_id,
        "title": "大黄鱼",
        "summary": "测试条目",
        "facts": [{"label": "学名", "value": "Larimichthys crocea"}],
        "as_of": "2026-11-03",
        "review_due": "2027-02-01",
        "status": "approved",
        "confidence": "high",
        "sources": [
            {
                "card": "WEB-TEST-001",
                "sha256": CARD_SHA,
                "url": "https://www.moa.gov.cn/x",
                "publisher": "农业农村部",
                "fetched_at": "2026-11-03",
            }
        ],
    }
    note.update(overrides)
    return note


def _dir(tmp_path: Path, notes: list[dict], topic: str = "species") -> Path:
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / f"{topic}.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "topic": topic, "notes": notes}, allow_unicode=True),
        encoding="utf-8",
    )
    return directory


def _cards(tmp_path: Path, sha: str = CARD_SHA) -> Path:
    path = tmp_path / "web-cards.yaml"
    path.write_text(
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
                        "sha256": sha,
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
    return path


def test_valid_note_loads(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note()])
    data = load_knowledge(directory / "species.yaml")
    assert data["notes"][0]["id"] == "KNO-SPECIES-001"
    assert list_notes(directory)[0]["topic"] == "species"


def test_missing_field_is_rejected(tmp_path: Path) -> None:
    note = _note()
    del note["summary"]
    directory = _dir(tmp_path, [note])
    with pytest.raises(KnowledgeError, match="missing summary"):
        load_knowledge(directory / "species.yaml")


def test_bad_id_is_rejected(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note("KNO-BAD-1")])
    with pytest.raises(KnowledgeError, match="id must match"):
        load_knowledge(directory / "species.yaml")


def test_changed_card_hash_marks_stale(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note()])
    cards = _cards(tmp_path, sha="b" * 64)
    report = check(directory, cards, today=date(2026, 11, 3), write=True)
    assert report["stale"] == 1
    assert "changed" in report["notes"][0]["reasons"][0]
    assert load_knowledge(directory / "species.yaml")["notes"][0]["status"] == "stale"


def test_expired_hazard_marks_stale(tmp_path: Path) -> None:
    note = _note(
        "KNO-HAZARD-001",
        topic="hazard",
        expires_at="2026-11-01",
        sources=[{"doc": "POL-TEST", "sha256": "c" * 64}],
    )
    directory = _dir(tmp_path, [note], topic="hazard")
    cards = _cards(tmp_path)
    report = check(directory, cards, today=date(2026, 11, 3), write=True)
    assert report["stale"] == 1


def test_past_review_is_due_but_not_stale(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note(as_of="2026-10-01", review_due="2026-11-01")])
    cards = _cards(tmp_path)
    report = check(directory, cards, today=date(2026, 11, 3))
    assert report["due"] == 1
    assert report["notes"][0]["status"] == "approved"
    assert report["notes"][0]["reasons"] == []


def test_approve_draft(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note(status="draft")])
    cards = _cards(tmp_path)
    # approve looks for cards beside the knowledge directory's parent
    (tmp_path / "web-cards.yaml").write_text(cards.read_text(encoding="utf-8"), encoding="utf-8")
    result = approve(directory, "KNO-SPECIES-001", today=date(2026, 11, 3))
    assert result["status"] == "approved"


def test_approve_refuses_stale(tmp_path: Path) -> None:
    directory = _dir(tmp_path, [_note(status="draft")])
    _cards(tmp_path, sha="b" * 64)
    with pytest.raises(KnowledgeError, match="cannot approve"):
        approve(directory, "KNO-SPECIES-001", today=date(2026, 11, 3))


def test_topic_counts_and_sources() -> None:
    import yaml as _yaml

    counts = {}
    for path in sorted(Path("configs/knowledge").glob("*.yaml")):
        data = _yaml.safe_load(path.read_text(encoding="utf-8"))
        counts[data["topic"]] = len(data["notes"])
    assert counts["species"] == 115
    assert counts["policy"] >= 7
    assert counts["gear"] >= 6
    assert counts["environment"] >= 2
    assert counts["hazard"] >= 4
    assert counts["stats"] >= 3
    total = sum(counts.values())
    assert total >= 130
    for path in Path("configs/knowledge").glob("*.yaml"):
        for note in _yaml.safe_load(path.read_text(encoding="utf-8"))["notes"]:
            assert note["sources"]
            for source in note["sources"]:
                assert len(source.get("sha256", "")) == 64
