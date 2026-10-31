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
    assert "categories" not in data
    assert len(data["types"]) == 8
    type_ids = {entry["id"] for entry in data["types"]}
    assert type_ids == {
        "statistical_yearbook",
        "operations",
        "law",
        "regulation",
        "notice",
        "standard",
        "fishery_product",
        "data_dictionary",
    }
    assert len(data["sources"]) == 27

    acquired = []
    candidates = []
    for source in data["sources"]:
        assert source["title"]
        assert source["title_zh"]
        assert source["type"] in type_ids
        if source["status"] == "acquired":
            acquired.append(source)
        else:
            candidates.append(source)

    assert len(acquired) == 18
    assert len(candidates) == 9
    yearbooks = [source for source in acquired if source["id"].startswith("STAT-YB-")]
    assert len(yearbooks) == 8
    assert [source["year"] for source in yearbooks] == list(range(2018, 2026))
    for source in yearbooks:
        assert source["type"] == "statistical_yearbook"
        assert source["license"] == "internal"
        assert source["sensitivity"] == "internal"
        assert source["location"] == f"raw/{source['id']}/"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["volume"].endswith("files")

    policy = [source for source in acquired if not source["id"].startswith("STAT-YB-")]
    assert {source["id"] for source in policy} == {
        "POL-LAW-009",
        "POL-STD-010",
        "POL-CLOS-015",
        "POL-RULE-018",
        "POL-RULE-019",
        "POL-RULE-020",
        "POL-GD-021",
        "POL-GD-022",
        "POL-GX-023",
        "POL-GX-024",
    }
    for source in policy:
        assert source["license"] == "public"
        assert source["sensitivity"] == "public"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["location"].startswith("raw/")
        assert not source["location"].startswith("/")
        assert source["jurisdiction"] in {"national", "guangdong", "guangxi"}

    for source in candidates:
        assert source["status"] == "to_acquire"
        assert source["location"] is None
        assert source["hash"] is None
        assert source["license"] == "unknown"
        assert source["sensitivity"] == "unknown"
        assert source["disposition"] in {"acquire", "defer"}
        assert source["disposition_reason"].strip()

    ids = {source["id"] for source in data["sources"]}
    assert "OPS-STAT-001" not in ids
    assert "LIT-PAPER-011" not in ids
    assert "LIT-RPT-012" not in ids
    type_counts = {
        type_id: sum(1 for source in data["sources"] if source["type"] == type_id)
        for type_id in type_ids
    }
    assert type_counts == {
        "statistical_yearbook": 8,
        "operations": 1,
        "law": 1,
        "regulation": 8,
        "notice": 1,
        "standard": 0,
        "fishery_product": 4,
        "data_dictionary": 4,
    }


def test_statistics_schema() -> None:
    data = load_yaml("configs/statistics.yaml")
    columns = {column["name"] for column in data["long_table"]["columns"]}
    assert {
        "data_year",
        "edition",
        "type",
        "region",
        "sea_area",
        "gear",
        "operation_type",
        "power_band",
        "length_band",
        "species",
        "indicator",
        "value",
        "unit",
        "basis",
        "table_id",
        "table_name",
        "source_file",
        "sheet",
        "row",
        "source_sha256",
    } <= columns
    assert set(data["indicator_groups"]) == {
        "capture",
        "vessels",
        "population",
        "economy",
        "infrastructure",
    }
    assert data["publication"]["values"] == "local_only"


def test_questions_count() -> None:
    text = (ROOT / "docs/questions.md").read_text(encoding="utf-8")
    assert text.count("| Q-E") == 12
    assert text.count("| Q-M") == 12
    assert "OPS-STAT-001" not in text


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
    for relative in ("configs/corpus.yaml", "configs/schema.yaml", "configs/statistics.yaml"):
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
