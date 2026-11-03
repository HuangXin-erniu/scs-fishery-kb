from __future__ import annotations

import json
from pathlib import Path

import yaml

from scs_fkb.knowledge_build import build_species_notes, species_card_id, species_note

CARD = {
    "id": "WEB-WORMS-LARIMICHTHYS-CROCEA",
    "title": "大黄鱼 Larimichthys crocea",
    "url": "https://www.marinespecies.org/rest/x",
    "sha256": "a" * 64,
    "fetched_at": "2026-11-03T00:00:00+00:00",
    "file": "WEB-WORMS-LARIMICHTHYS-CROCEA/text.txt",
    "status": "ok",
}


def test_species_card_id_slug() -> None:
    assert species_card_id("Larimichthys crocea") == "WEB-WORMS-LARIMICHTHYS-CROCEA"
    assert species_card_id("Psenopsis anomala") == "WEB-WORMS-PSENOPSIS-ANOMALA"


def test_species_note_from_record() -> None:
    text = json.dumps(
        [
            {
                "scientificname": "Larimichthys crocea",
                "authority": "(Richardson, 1846)",
                "phylum": "Chordata",
                "class": "Teleostei",
                "order": "Eupercaria",
                "family": "Sciaenidae",
                "isMarine": 1,
                "isBrackish": 1,
                "isFreshwater": 0,
                "AphiaID": 281271,
            }
        ]
    )
    note = species_note(CARD, text, 5)
    assert note is not None
    assert note["id"] == "KNO-SPECIES-005"
    assert note["sources"][0]["card"] == CARD["id"]
    assert note["sources"][0]["sha256"] == CARD["sha256"]
    labels = {fact["label"] for fact in note["facts"]}
    assert {"学名", "命名人", "分类", "海洋/淡水", "WoRMS ID"} == labels


def test_species_note_skips_empty_record() -> None:
    assert species_note(CARD, "[]", 5) is None
    assert species_note(CARD, "not json", 5) is None


def test_build_skips_duplicates_and_missing(tmp_path: Path) -> None:
    cards = tmp_path / "web-cards.yaml"
    cards.write_text(
        yaml.safe_dump({"schema_version": 1, "cards": [CARD]}, allow_unicode=True),
        encoding="utf-8",
    )
    cache = tmp_path / "web"
    (cache / "WEB-WORMS-LARIMICHTHYS-CROCEA").mkdir(parents=True)
    (cache / "WEB-WORMS-LARIMICHTHYS-CROCEA" / "text.txt").write_text(
        json.dumps([{"scientificname": "Larimichthys crocea", "AphiaID": 1}]),
        encoding="utf-8",
    )
    knowledge = tmp_path / "species.yaml"
    knowledge.write_text(
        yaml.safe_dump({"schema_version": 1, "topic": "species", "notes": []}, allow_unicode=True),
        encoding="utf-8",
    )
    seed = tmp_path / "seed.yaml"
    seed.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "species": [
                    {"zh": "大黄鱼", "scientific": "Larimichthys crocea"},
                    {"zh": "未知种", "scientific": "Nonexistent species"},
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    report = build_species_notes(cards, cache, knowledge, seed)
    assert report["added"] == ["KNO-SPECIES-001"]
    assert report["skipped"][0]["scientific"] == "Nonexistent species"
    data = yaml.safe_load(knowledge.read_text(encoding="utf-8"))
    assert len(data["notes"]) == 1
    # a second run does not duplicate the existing species
    again = build_species_notes(cards, cache, knowledge, seed)
    assert again["added"] == []
