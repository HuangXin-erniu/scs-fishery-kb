from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_corpus_structure() -> None:
    data = load_yaml("configs/corpus.yaml")
    assert len(data["categories"]) == 7
    assert len(data["sources"]) == 14
    counts = {category["id"]: 0 for category in data["categories"]}
    for source in data["sources"]:
        counts[source["category"]] += 1
        assert source["status"] == "to_acquire"
        assert source["location"] is None
        assert source["hash"] is None
        assert source["license"] == "unknown"
        assert source["sensitivity"] == "unknown"
        assert source["title"]
        assert source["title_zh"]
    assert set(counts.values()) == {2}


def test_questions_count() -> None:
    text = (ROOT / "docs/questions.md").read_text(encoding="utf-8")
    assert text.count("| Q-E") == 12
    assert text.count("| Q-M") == 12


def test_citation_metadata() -> None:
    data = load_yaml("CITATION.cff")
    assert data["title"].startswith("South China Sea Nearshore Fishery Knowledge Base")
    assert data["version"] == "0.1.0-alpha"
    assert data["license"] == "Apache-2.0"


def test_schema_sections() -> None:
    data = load_yaml("configs/schema.yaml")
    for section in ("document", "chunk", "citation", "sensitivity"):
        assert section in data
