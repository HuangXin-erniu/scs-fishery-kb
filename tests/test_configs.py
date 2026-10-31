from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".cff", ".py", ".sh"}
TEXT_NAMES = {"LICENSE", "LICENSE-docs", "NOTICE", "Makefile"}
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "data", "runs"}
VERSION_MARKERS = ["v0." + "1.0", "0.1.0" + "-alpha"]


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
    assert data["license"] == "Apache-2.0"
    assert data["repository-code"].endswith("scs-fishery-kb")
    assert "version" not in data
    assert "date-released" not in data


def test_schema_sections() -> None:
    data = load_yaml("configs/schema.yaml")
    for section in ("document", "chunk", "citation", "sensitivity"):
        assert section in data


def test_config_schema_version_key() -> None:
    for relative in ("configs/corpus.yaml", "configs/schema.yaml"):
        data = load_yaml(relative)
        assert data["schema_version"] == 1
        assert "version" not in data


def test_no_git_tags() -> None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_framework_documents_exist() -> None:
    for relative in (
        "docs/architecture.md",
        "docs/plan.md",
        "docs/evaluation.md",
        "docs/project-log.md",
    ):
        assert (ROOT / relative).is_file(), relative


def test_no_versioned_release_markers() -> None:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in VERSION_MARKERS:
            if marker in text:
                hits.append(f"{path.relative_to(ROOT)}: {marker}")
    assert not hits, hits
