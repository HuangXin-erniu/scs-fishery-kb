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
    assert len(data["types"]) == 9
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
        "plan",
    }
    assert len(data["sources"]) == 43

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

    assert len(acquired) == 40
    assert len(candidates) == 3
    yearbooks = [source for source in acquired if source["id"].startswith("STAT-YB-")]
    assert len(yearbooks) == 9
    assert [source["year"] for source in yearbooks] == list(range(2018, 2027))
    for source in yearbooks:
        assert source["type"] == "statistical_yearbook"
        assert source["license"] == "internal"
        assert source["sensitivity"] == "internal"
        assert source["location"] == f"raw/{source['id']}/"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["volume"].endswith(("files", "pages"))

    documents = [source for source in acquired if source["type"] != "statistical_yearbook"]
    assert {source["id"] for source in documents} == {
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
        "POL-FJ-025",
        "POL-FJ-026",
        "POL-GEAR-033",
        "POL-GEAR-034",
        "OPS-STD-035",
        "OPS-FORM-036",
        "POL-PORT-037",
        "POL-PLAN-038",
        "POL-GEAR-016",
        "OPS-STD-039",
        "POL-SPEC-041",
        "STD-SC-042",
        "DICT-STAT-013",
        "DICT-STAT-040",
    }
    for source in documents:
        if source["id"] == "STD-SC-042":
            continue
        assert source["license"] == "public"
        assert source["sensitivity"] == "public"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["location"].startswith("raw/")
        assert not source["location"].startswith("/")
        assert source["jurisdiction"] in {"national", "guangdong", "guangxi", "fujian"}

    series = [source for source in acquired if source["id"] == "STD-SC-042"]
    assert len(series) == 1
    assert series[0]["type"] == "standard"
    assert series[0]["format"] == "pdf"
    assert series[0]["license"] == "internal"
    assert series[0]["sensitivity"] == "internal"
    assert series[0]["location"] == "raw/SC-STD/"
    assert "17 standards" in series[0]["volume"]
    assert re.fullmatch(r"[0-9a-f]{64}", series[0]["hash"])

    special = [source for source in acquired if source["id"] == "POL-SPEC-041"]
    assert len(special) == 1
    assert special[0]["type"] == "notice"
    assert special[0]["format"] == "ofd"
    assert special[0]["location"].endswith(".ofd")
    assert special[0]["hash"].startswith("b383ea35")
    assert "22 pages" in special[0]["volume"]
    assert "Sthenoteuthis oualaniensis" in special[0]["notes"]

    scan = [source for source in acquired if source["id"] == "STAT-YB-2026"]
    assert len(scan) == 1
    assert scan[0]["format"] == "pdf"
    assert scan[0]["license"] == "internal"
    assert "scanned pages" in scan[0]["volume"]
    assert "OCR" in scan[0]["notes"]

    bulletin = [source for source in acquired if source["id"] == "STAT-BULL-025"]
    assert len(bulletin) == 1
    assert bulletin[0]["type"] == "statistical_yearbook"
    assert bulletin[0]["format"] == "html"
    assert bulletin[0]["jurisdiction"] == "national"
    assert bulletin[0]["license"] == "public"
    assert re.fullmatch(r"[0-9a-f]{64}", bulletin[0]["hash"])

    bulletins = [source for source in acquired if source["id"].startswith("STAT-BULL-")]
    assert {source["id"] for source in bulletins} == {
        "STAT-BULL-025",
        "STAT-BULL-028",
        "STAT-BULL-029",
        "STAT-BULL-030",
        "STAT-BULL-031",
        "STAT-BULL-032",
    }
    for source in bulletins:
        assert source["type"] == "statistical_yearbook"
        assert source["format"] == "html"
        assert source["jurisdiction"] == "national"
        assert source["license"] == "public"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])

    csy = [source for source in acquired if source["id"] == "STAT-CSY-027"]
    assert len(csy) == 1
    assert csy[0]["type"] == "statistical_yearbook"
    assert csy[0]["format"] == "xlsx"
    assert csy[0]["license"] == "internal"
    assert csy[0]["jurisdiction"] == "national"
    assert re.fullmatch(r"[0-9a-f]{64}", csy[0]["hash"])

    dictionaries = [source for source in acquired if source["type"] == "data_dictionary"]
    assert {source["id"] for source in dictionaries} == {"DICT-STAT-013", "DICT-STAT-040"}
    for source in dictionaries:
        assert source["license"] == "public"
        assert source["jurisdiction"] == "national"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["location"].startswith("raw/")

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
    assert "OPS-LOG-002" not in ids
    assert "DICT-STAT-026" not in ids
    assert "LIT-PAPER-011" not in ids
    assert "LIT-RPT-012" not in ids
    type_counts = {
        type_id: sum(1 for source in data["sources"] if source["type"] == type_id)
        for type_id in type_ids
    }
    assert type_counts == {
        "statistical_yearbook": 16,
        "law": 1,
        "regulation": 10,
        "notice": 4,
        "standard": 5,
        "operations": 1,
        "fishery_product": 0,
        "data_dictionary": 5,
        "plan": 1,
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
    regions = set(data["dimensions"]["region"]["values"])
    assert {"China", "Guangdong", "Guangxi", "Hainan", "Fujian"} <= regions


def test_questions_count() -> None:
    text = (ROOT / "docs/questions.md").read_text(encoding="utf-8")
    assert text.count("| Q-E") == 12
    assert text.count("| Q-M") == 12
    assert "OPS-STAT-001" not in text
    for removed in ("OPS-LOG-002", "ENV-SST-005", "ENV-CHL-006", "FCS-BULL-007", "FCS-REC-008"):
        assert removed not in text


def test_documents_do_not_cite_closed_sources() -> None:
    for relative in ("docs/corpus.md", "docs/plan.md", "docs/questions.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "OPS-LOG-002" not in text, relative


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


def test_standards_catalog() -> None:
    data = load_yaml("configs/sc-standards.yaml")
    assert data["schema_version"] == 1
    assert data["series"] == "STD-SC-042"
    entries = data["standards"]
    assert len(entries) == data["acquired"] == 17
    assert "no_public_text" not in data
    assert "relevant_standards" not in data
    assert "not_available" not in data
    codes = [entry["code"] for entry in entries]
    assert len(codes) == len(set(codes))
    assert codes == sorted(codes)
    for entry in entries:
        assert entry["code"].startswith("SC/T ")
        assert entry["name_zh"].strip()
        assert entry["pages"] >= 1
        assert re.fullmatch(r"[0-9a-f]{16}", entry["sha256"])
