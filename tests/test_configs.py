from __future__ import annotations

import re
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
    assert len(data["sources"]) == 15

    counts = {category["id"]: 0 for category in data["categories"]}
    acquired = []
    candidates = []
    for source in data["sources"]:
        counts[source["category"]] += 1
        assert source["title"]
        assert source["title_zh"]
        if source["status"] == "acquired":
            acquired.append(source)
        else:
            candidates.append(source)

    assert counts["policy_standards"] == 3
    assert all(count == 2 for category, count in counts.items() if category != "policy_standards")

    assert len(acquired) == 3
    assert {source["id"] for source in acquired} == {
        "POL-LAW-009",
        "POL-STD-010",
        "POL-CLOS-015",
    }
    for source in acquired:
        assert source["license"] == "public"
        assert source["sensitivity"] == "public"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["location"].startswith("raw/")
        assert not source["location"].startswith("/")

    assert len(candidates) == 12
    for source in candidates:
        assert source["status"] == "to_acquire"
        assert source["location"] is None
        assert source["hash"] is None
        assert source["license"] == "unknown"
        assert source["sensitivity"] == "unknown"


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


def test_data_root_is_external() -> None:
    data = load_yaml("configs/corpus.yaml")
    assert data["data_root"] is None
    assert data["data_root_env"] == "SCS_FKB_DATA_ROOT"


def test_no_local_data_directories() -> None:
    for name in ("data", "runs"):
        assert not (ROOT / name).exists(), f"{name}/ must live outside the repository"


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


def test_bilingual_entry_points() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    project_zh = (ROOT / "PROJECT.zh-CN.md").read_text(encoding="utf-8")
    assert "[简体中文](README.zh-CN.md)" in readme
    assert "[English](README.md)" in readme_zh
    assert "[English](PROJECT.md)" in project_zh


def test_chinese_summaries() -> None:
    for relative in (
        "docs/architecture.md",
        "docs/plan.md",
        "docs/evaluation.md",
        "docs/data-policy.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "**中文摘要**" in text, relative


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
