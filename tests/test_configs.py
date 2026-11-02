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
    assert len(data["sources"]) == 55

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

    assert len(acquired) == 52
    assert len(candidates) == 3
    yearbooks = [source for source in acquired if source["id"].startswith("STAT-YB-")]
    assert len(yearbooks) == 9
    assert [source["year"] for source in yearbooks] == list(range(2018, 2027))
    for source in yearbooks:
        assert source["type"] == "statistical_yearbook"
        assert source["jurisdiction"] == "national"
        assert source["license"] == "internal"
        assert source["sensitivity"] == "internal"
        assert source["location"] == f"raw/{source['id']}/"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["volume"].endswith(("files", "pages"))

    jurisdictions = {"national", "guangdong", "guangxi", "fujian", "international"}
    for source in acquired:
        assert source.get("jurisdiction") in jurisdictions, source["id"]

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
        "STD-ASFIS-044",
        "STD-CWP-043",
        "STD-MUR-045",
        "STD-OLCI-046",
        "DICT-GFW-047",
        "DICT-GFW-048",
        "STD-CMEMS-049",
        "POL-STAT-050",
        "POL-STAT-051",
        "POL-YJ-052",
        "POL-VMS-053",
        "STD-ECERT-054",
    }
    for source in documents:
        if source["id"] in {
            "STD-SC-042",
            "STD-ASFIS-044",
            "STD-CWP-043",
            "STD-MUR-045",
            "STD-OLCI-046",
            "DICT-GFW-047",
            "DICT-GFW-048",
            "STD-CMEMS-049",
            "POL-STAT-050",
            "POL-STAT-051",
            "POL-YJ-052",
            "POL-VMS-053",
            "STD-ECERT-054",
        }:
            continue
        assert source["license"] == "public"
        assert source["sensitivity"] == "public"
        assert re.fullmatch(r"[0-9a-f]{64}", source["hash"])
        assert source["location"].startswith("raw/")
        assert not source["location"].startswith("/")
        assert source["jurisdiction"] in {
            "national",
            "guangdong",
            "guangxi",
            "fujian",
            "international",
        }

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
    assert {source["id"] for source in dictionaries} == {
        "DICT-STAT-013",
        "DICT-STAT-040",
        "STD-ASFIS-044",
        "DICT-GFW-047",
        "DICT-GFW-048",
    }
    international = {"STD-ASFIS-044", "DICT-GFW-047", "DICT-GFW-048"}
    for source in dictionaries:
        if source["id"] in international:
            continue
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
        "regulation": 13,
        "notice": 5,
        "standard": 7,
        "operations": 1,
        "fishery_product": 3,
        "data_dictionary": 8,
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


def test_pipeline_config() -> None:
    pipeline = load_yaml("configs/pipeline.yaml")
    assert pipeline["schema_version"] == 1
    documents = pipeline["documents"]
    assert len(documents) == 29
    assert len(set(documents)) == 29
    assert pipeline["chunking"]["max_fallback_chars"] >= 200

    corpus = load_yaml("configs/corpus.yaml")
    by_id = {source["id"]: source for source in corpus["sources"]}
    for doc_id in documents:
        assert doc_id in by_id, doc_id
        source = by_id[doc_id]
        assert source["status"] == "acquired"
        assert source["sensitivity"] == "public"
        assert source["format"] in {"html", "docx", "ofd", "pdf", "doc"}


def test_eval_config() -> None:
    config = load_yaml("configs/eval.yaml")
    assert config["schema_version"] == 1
    assert len(config["anchors"]) == 11
    assert len(config["abstention"]) == 6
    corpus = {source["id"] for source in load_yaml("configs/corpus.yaml")["sources"]}
    for question_id, entries in config["anchors"].items():
        assert question_id.startswith("Q-")
        assert 1 <= len(entries) <= 3
        for entry in entries:
            assert entry["doc"] in corpus
    assert set(config["abstention"]).isdisjoint(config["anchors"])


def test_international_references() -> None:
    data = load_yaml("configs/corpus.yaml")
    by_id = {source["id"]: source for source in data["sources"]}
    cwp = by_id["STD-CWP-043"]
    assert cwp["type"] == "standard"
    assert cwp["jurisdiction"] == "international"
    assert cwp["license"] == "cc-by-nc-sa-3.0-igo"
    assert cwp["location"] == "raw/STD-CWP-043/"
    assert "not a Chinese official definition" in cwp["notes"]

    asfis = by_id["STD-ASFIS-044"]
    assert asfis["type"] == "data_dictionary"
    assert asfis["jurisdiction"] == "international"
    assert asfis["license"] == "cc-by-nc-sa-3.0-igo"
    assert asfis["location"] == "raw/STD-ASFIS-044/"

    pipeline = load_yaml("configs/pipeline.yaml")
    assert cwp["id"] not in pipeline["documents"]
    assert asfis["id"] not in pipeline["documents"]


def test_cwp_catalog() -> None:
    import hashlib

    data = load_yaml("configs/cwp-handbook.yaml")
    assert data["series"] == "STD-CWP-043"
    assert data["license"] == "cc-by-nc-sa-3.0-igo"
    pages = data["pages"]
    assert len(pages) == data["documents"] == 3
    for page in pages:
        assert re.fullmatch(r"[0-9a-f]{64}", page["sha256"])
        assert page["bytes"] > 0
        assert page["chars"] > 0
        assert page["url"].startswith("https://www.fao.org/")
    computed = hashlib.sha256("".join(page["sha256"] for page in pages).encode()).hexdigest()
    assert computed == data["manifest_sha256"]


def test_glossary_bridge() -> None:
    data = load_yaml("configs/glossary-bridge.yaml")
    assert data["schema_version"] == 1
    terms = data["terms"]
    assert len(terms) >= 5
    seen = set()
    for entry in terms:
        assert entry["zh"] not in seen
        seen.add(entry["zh"])
        assert entry["en"] and all(isinstance(item, str) and item for item in entry["en"])
        assert entry["note"]
    assert {"产量", "上岸量", "捕捞努力量"} <= seen


def test_eval_reference_section() -> None:
    config = load_yaml("configs/eval.yaml")
    reference = config["reference"]
    assert [item["id"] for item in reference] == ["Q-E05", "Q-M04"]
    for item in reference:
        assert item["docs"] == ["STD-CWP-043-catch", "STD-CWP-043-effort"]


def test_lexicon_config() -> None:
    data = load_yaml("configs/lexicon.yaml")
    assert data["schema_version"] == 1
    active = data["groups"]
    assert [group["term"] for group in active] == ["例外"]
    assert active[0]["variants"] == ["专项", "特许"]
    rejected = data["rejected"]
    assert [group["term"] for group in rejected] == ["休渔", "捕捞日志", "准入", "网目"]
    assert all(group["note"] for group in active + rejected)
    pipeline = load_yaml("configs/pipeline.yaml")
    assert pipeline["retrieval"]["lexicon_expand"] is True


def test_retrieval_mode_config() -> None:
    pipeline = load_yaml("configs/pipeline.yaml")
    retrieval = pipeline["retrieval"]
    assert retrieval["mode"] == "hybrid"
    assert retrieval["lexicon_expand"] is True
    assert retrieval["fusion_k"] == 60
    assert retrieval["bm25_weight"] == 2.0
    assert retrieval["dense_weight"] == 1.0
    assert pipeline["answer"]["min_score"] == 19.0


def test_eval_statistics_section() -> None:
    config = load_yaml("configs/eval.yaml")
    entries = config["statistics"]
    assert [item["id"] for item in entries] == ["Q-E06", "Q-M05"]
    assert [item["expect"] for item in entries] == ["capture_production_sea_area", "vessel_count"]


def test_remote_stack_documents() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    expected = {
        "STD-MUR-045": ("fishery_product", "cc-by-4.0"),
        "STD-OLCI-046": ("fishery_product", "public"),
        "DICT-GFW-047": ("data_dictionary", "unknown"),
        "DICT-GFW-048": ("data_dictionary", "apache-2.0"),
        "STD-CMEMS-049": ("fishery_product", "public"),
    }
    for source_id, (source_type, licence) in expected.items():
        source = sources[source_id]
        assert source["type"] == source_type
        assert source["license"] == licence
        assert source["status"] == "acquired"
        assert source["jurisdiction"] == "international"
        assert source["location"].startswith(f"raw/{source_id}/")
        assert len(source["hash"]) == 64


def test_statistical_governance_documents() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    expected = {
        "POL-STAT-050": ("regulation", "P1"),
        "POL-STAT-051": ("regulation", "P1"),
        "POL-YJ-052": ("notice", "P2"),
        "POL-VMS-053": ("regulation", "P2"),
        "STD-ECERT-054": ("standard", "P2"),
    }
    for source_id, (source_type, priority) in expected.items():
        source = sources[source_id]
        assert source["type"] == source_type
        assert source["priority"] == priority
        assert source["status"] == "acquired"
        assert source["jurisdiction"] == "national"
        assert source["license"] == "public"
        assert source["location"].startswith(f"raw/{source_id}/")
        assert len(source["hash"]) == 64
    assert "国统制〔2024〕120号" in sources["POL-STAT-051"]["notes"]
    assert "农办渔〔2018〕30号" in sources["POL-YJ-052"]["volume"]


def test_reference_collections_config() -> None:
    data = load_yaml("configs/reference-collections.yaml")
    collections = data["collections"]
    assert set(collections) == {"product", "policy"}
    product_ids = {doc["id"] for doc in collections["product"]["documents"]}
    policy_ids = {doc["id"] for doc in collections["policy"]["documents"]}
    assert product_ids == {
        "STD-MUR-045",
        "STD-OLCI-046",
        "DICT-GFW-047",
        "DICT-GFW-048",
        "STD-CMEMS-049",
    }
    assert policy_ids == {
        "POL-STAT-050",
        "POL-STAT-051",
        "POL-YJ-052",
        "POL-VMS-053",
        "STD-ECERT-054",
    }
    corpus = {source["id"]: source for source in load_yaml("configs/corpus.yaml")["sources"]}
    for collection in collections.values():
        for document in collection["documents"]:
            relative = document.get("file") or document.get("location") or ""
            assert relative.startswith(f"raw/{document['id']}/")
            assert collection is collections["policy"] or document["language"] == "en"
            assert len(document["sha256"]) == 64
            assert document["id"] in corpus
