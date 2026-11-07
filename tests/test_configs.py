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
    assert len(data["sources"]) == 99

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

    assert len(acquired) == 99
    assert len(candidates) == 0
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
        assert source["volume"].endswith(("files", "pages", "page"))

    jurisdictions = {"national", "guangdong", "guangxi", "hainan", "fujian", "international"}
    for source in acquired:
        assert source.get("jurisdiction") in jurisdictions, source["id"]

    documents = [source for source in acquired if source["type"] != "statistical_yearbook"]
    assert {source["id"] for source in documents} == {
        "POL-LAW-009",
        "POL-STD-010",
        "POL-CREW-055",
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
        "POL-GEAR-016",
        "OPS-STD-039",
        "POL-SPEC-041",
        "DICT-STAT-013",
        "DICT-STAT-040",
        "STD-CWP-043",
        "POL-STAT-050",
        "POL-STAT-051",
        "POL-VMS-053",
        "STD-ECERT-054",
        "POL-HN-058",
        "POL-HN-059",
        "POL-GX-060",
        "POL-GD-061",
        "STD-HULL-062",
        "POL-FJ-063",
        "STD-FJ-064",
        "STD-FJ-065",
        "STD-FJ-066",
        "STD-GD-064",
        "STD-GD-065",
        "STD-HN-066",
        "STD-HN-067",
        "POL-ENF-068",
        "STD-HULL-069",
        "STD-HULL-070",
        "STD-YY-071",
        "POL-OBS-072",
        "STAT-ECO-073",
        "STAT-DIS-074",
        "POL-RES-075",
        "STD-SPEC-076",
        "POL-PORT-077",
        "POL-LAW-097",
        "POL-LAW-098",
        "POL-LAW-099",
        "POL-REG-101",
        "POL-GEAR-102",
        "POL-PEN-103",
        "POL-LAW-100",
        "STD-WQ-104",
        "PAPER-105",
        "PAPER-106",
        "PAPER-107",
        "POL-HN-108",
        "POL-QZ-109",
        "POL-GD-110",
        "POL-LAW-116",
        "STD-EUTRO-119",
        "POL-TURTLE-113",
        "STD-SMALL-114",
        "POL-JUD-115",
        "POL-DOLPHIN-117",
        "POL-GX-118",
        "STAT-ECO-111",
        "POL-PEN-078",
        "POL-LIST-079",
        "POL-PEN-080",
        "POL-WATCH-082",
        "POL-CREW-083",
        "POL-CODE-084",
        "POL-ID-085",
        "POL-SANWU-086",
        "POL-FUEL-087",
        "POL-STAT-088",
        "POL-RED-089",
        "POL-CONS-090",
        "POL-MIN-091",
        "INT-SUS-092",
        "POL-MARKET-093",
        "INT-MSY-095",
        "POL-SUB-094",
        "POL-OCEAN-096",
    }
    for source in documents:
        if source["id"] in {
            "STD-CWP-043",
            "POL-STAT-050",
            "POL-STAT-051",
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
            "hainan",
            "fujian",
            "international",
        }

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

    bulletins = [source for source in acquired if source["id"].startswith("STAT-BULL-")]
    assert {source["id"] for source in bulletins} == set()
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
        "POL-STAT-088",
    }
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
        "statistical_yearbook": 10,
        "law": 6,
        "regulation": 23,
        "notice": 26,
        "standard": 21,
        "operations": 1,
        "fishery_product": 5,
        "data_dictionary": 3,
        "plan": 4,
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
    assert text.count("| Q-E") == 15
    assert text.count("| Q-M") == 18
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
    for relative in ("configs/corpus.yaml", "configs/schema.yaml"):
        assert load_yaml(relative)["source_record_schema"] == 4


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
    assert len(documents) == 48
    assert len(set(documents)) == 48
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
    assert len(config["anchors"]) == 31
    assert len(config["abstention"]) == 11
    corpus = {source["id"] for source in load_yaml("configs/corpus.yaml")["sources"]}
    for question_id, entries in config["anchors"].items():
        assert question_id.startswith("Q-")
        assert 1 <= len(entries) <= 3
        for entry in entries:
            assert entry["doc"] in corpus
    assert set(config["abstention"]).isdisjoint(config["anchors"])


def test_eval_split_and_persona() -> None:
    config = load_yaml("configs/eval.yaml")
    meta = config["meta"]
    assert len(meta) == 48
    scored = set(config["anchors"]) | set(config["abstention"])
    assert scored <= set(meta)
    split = {question_id: item["split"] for question_id, item in meta.items()}
    assert sum(1 for value in split.values() if value == "dev") == 33
    assert sum(1 for value in split.values() if value == "test") == 15
    test_ids = {question_id for question_id, value in split.items() if value == "test"}
    assert test_ids == {
        "Q-C01",
        "Q-C02",
        "Q-C03",
        "Q-C04",
        "Q-O01",
        "Q-O02",
        "Q-O03",
        "Q-O04",
        "Q-F01",
        "Q-F02",
        "Q-F03",
        "Q-F04",
        "Q-T01",
        "Q-T02",
        "Q-T03",
    }
    assert (
        test_ids & {question_id for question_id, value in split.items() if value == "dev"} == set()
    )
    personas = {question_id: item["persona"] for question_id, item in meta.items()}
    assert {personas[question_id] for question_id in test_ids} == {
        "captain",
        "owner",
        "enforcement",
        "extension",
    }
    assert sum(1 for question_id in test_ids if personas[question_id] == "captain") == 4
    assert sum(1 for question_id in test_ids if personas[question_id] == "owner") == 4
    assert sum(1 for question_id in test_ids if personas[question_id] == "enforcement") == 4
    assert sum(1 for question_id in test_ids if personas[question_id] == "extension") == 3
    assert {
        question_id for question_id in config["anchors"] if question_id in test_ids
    } == test_ids - {"Q-C04", "Q-O04", "Q-T03"}
    assert {question_id for question_id in config["abstention"] if question_id in test_ids} == {
        "Q-C04",
        "Q-O04",
        "Q-T03",
    }


def test_international_references() -> None:
    data = load_yaml("configs/corpus.yaml")
    by_id = {source["id"]: source for source in data["sources"]}
    cwp = by_id["STD-CWP-043"]
    assert cwp["type"] == "standard"
    assert cwp["jurisdiction"] == "international"
    assert cwp["license"] == "cc-by-nc-sa-3.0-igo"
    assert cwp["location"] == "raw/STD-CWP-043/"
    assert "not a Chinese official definition" in cwp["notes"]

    pipeline = load_yaml("configs/pipeline.yaml")
    assert cwp["id"] not in pipeline["documents"]
    for removed in (
        "STD-MUR-045",
        "STD-OLCI-046",
        "DICT-GFW-048",
        "STD-CMEMS-049",
        "STD-HY1-056",
        "STD-ASFIS-044",
    ):
        assert removed not in by_id


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
    assert {"水色", "覆盖周期", "重访", "幅宽"} <= seen


def test_eval_reference_section() -> None:
    config = load_yaml("configs/eval.yaml")
    reference = config["reference"]
    assert [item["id"] for item in reference] == ["Q-E05", "Q-M04"]
    assert [item.get("collection") for item in reference] == ["cwp", "cwp"]
    assert reference[0]["docs"] == ["STD-CWP-043-catch", "STD-CWP-043-effort"]
    assert config["web"] == []


def test_lexicon_config() -> None:
    data = load_yaml("configs/lexicon.yaml")
    assert data["schema_version"] == 1
    active = data["groups"]
    assert [group["term"] for group in active] == ["例外", "起止日期"]
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
    assert pipeline["answer"]["min_score"] == 23.0


def test_eval_statistics_section() -> None:
    config = load_yaml("configs/eval.yaml")
    entries = config["statistics"]
    assert [item["id"] for item in entries] == ["Q-E06", "Q-M05"]
    assert [item["expect"] for item in entries] == ["capture_production_sea_area", "vessel_count"]


def test_statistical_governance_documents() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    expected = {
        "POL-STAT-050": ("regulation", "P1"),
        "POL-STAT-051": ("regulation", "P1"),
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


def test_reference_collections_config() -> None:
    data = load_yaml("configs/reference-collections.yaml")
    collections = data["collections"]
    assert set(collections) == {"policy"}
    policy_ids = {doc["id"] for doc in collections["policy"]["documents"]}
    assert policy_ids == {
        "POL-STAT-050",
        "POL-STAT-051",
        "POL-VMS-053",
        "STD-ECERT-054",
        "POL-CREW-055",
        "POL-HN-058",
        "POL-HN-059",
        "POL-GX-060",
        "POL-GD-061",
        "STD-HULL-062",
        "POL-FJ-063",
        "STD-FJ-064",
        "STD-FJ-065",
        "STD-FJ-066",
        "STD-GD-064",
        "STD-GD-065",
        "STD-HN-066",
        "STD-HN-067",
        "POL-ENF-068",
        "STD-HULL-069",
        "STD-HULL-070",
        "STD-YY-071",
        "POL-OBS-072",
        "STAT-ECO-073",
        "POL-RES-075",
        "POL-PORT-077",
        "POL-PEN-078",
        "POL-LIST-079",
        "POL-PEN-080",
        "POL-WATCH-082",
    }
    for document in collections["policy"]["documents"]:
        assert document["level"] in {"national", "provincial", "municipal"}
        assert document["jurisdiction"] in {
            "national",
            "hainan",
            "guangxi",
            "guangdong",
            "fujian",
        }
    corpus = {source["id"]: source for source in load_yaml("configs/corpus.yaml")["sources"]}
    for collection in collections.values():
        for document in collection["documents"]:
            relative = document.get("file") or document.get("location") or ""
            assert relative.startswith(f"raw/{document['id']}/")
            assert document["language"] in {"en", "zh"}
            assert len(document["sha256"]) == 64
            assert document["id"] in corpus


def test_corrected_corpus_hashes() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    expected = {
        "POL-STAT-050": "1395e5dbd075b405a9de039d213aa2126bb5d452f56f8795c77af22634d2884a",
        "POL-STAT-051": "ee29cca7e24cd18d5f4eb11c6b4219060143cb641f5d64610e8dd67f6980cf97",
        "POL-VMS-053": "307a185fc27b3584f0fb39e97f31813ce1ac7d00c9bfc4f7bb9d8e1f731a8d41",
        "POL-HN-058": "554997f45e7215751bd17a27f9389703eb5735611c43178834763ac499179c0d",
        "POL-HN-059": "f8bb3e3f5ad8cf9be7fe697fd811b069d353fb6e1d2a4a8b3bbe29779065a756",
        "POL-GX-060": "b9028450c6f0a587b35a866b759ca503f6f69415c744b32aa5845cbfe31ea516",
        "POL-GD-061": "1194cd62c59f176bb70e0f04db4c9873e1f322a37e30eac1627f61cb132a602e",
        "STD-HULL-062": "e6e94a8aaf1bffdb11229204aca667971b71a1550ae0c818dd94ce6f05904bce",
        "POL-FJ-063": "6def833b7a5eecba15e4f46f4e5985dc8e36fd6c9ee4565bb742a50a5743851c",
        "STD-FJ-064": "11b7e632e969039a417c09878fba12e59b657b09439754cbf7f7453ff39a15c9",
        "STD-FJ-065": "693e4fd69a61d505f523f2e41cb1f59ca64e739b6dd3f5dc2b231e7e3b439677",
        "STD-FJ-066": "38d52286e5c5ba9498d848a090c546d31137df9c78f0faee53af521768de04ce",
        "STD-GD-064": "b8e829a4d86aecadb7fe1447fdefea1314a782bcbb142067d2719ad904120cd8",
        "STD-GD-065": "f6ed423220baca5ec45b9b83fe583c39093245194dba70c8417fea63ab0961ad",
        "STD-HN-066": "4db86b28b700267efadf4f942258a1d835122946270269a265e2fc10836b1392",
        "STD-HN-067": "6b5bebcc6d2278a7b27d5a1ba2e581871b49f551e966fcadbc7d9890772ed709",
        "POL-ENF-068": "174ab3e343df18e09d8340272e329d956b062ce909216eea8282e206a6bca8af",
        "STD-HULL-069": "822a8c089528438ad1b6cf353df94403711e86ebf6a9197443b14987bdb7a316",
        "STD-HULL-070": "f2e5f2f81200f3f69476f1792b5bd73658c9393b20932e5f62ac56a6fa44c6ef",
        "STD-YY-071": "29b1f6afcf88c84d6a777d571036d1173467bc3823b936422d3e45111d1a2668",
        "POL-OBS-072": "2ff2302e890798305958f38b1e21cbf0e6f2ddaea2d2619edd94c699c9b03af6",
        "STAT-ECO-073": "a263e432d33b19dfbb012600789aef84e84bfaef4a9bdd931714cd04f2ca621f",
        "STAT-DIS-074": "d280c286c9c048707a92112101e3ab0a295c9cde23815bbe8c90a63a4acfb671",
        "POL-RES-075": "90abf8647b254325125ed7f79bff16a4c573aab0a773fb166fb0dc79c3ec5971",
        "STD-SPEC-076": "8b45d11547577041e15c5837a3ff8f283d2dd2c2b87f83eb8026ad3feb8662c3",
        "POL-PORT-077": "1ff9570272738ada371f4e412c3b47ef13eaf94c68481a31640421fda6fc1fd2",
        "POL-PEN-078": "42884cb595529b9f687a4442ff5a8bf8f5706c5764cbb7df57859e29923bc428",
        "POL-LIST-079": "67c8240cc5bf63487b7ee43af3ea9800f41f60a29eeccbaa2c5b6f0feac9b29f",
        "POL-PEN-080": "57027911e2ce6b23d6e84aee6269f19623b19f927cdb31fcbad606e032756e81",
        "POL-WATCH-082": "8eecbc9171dbc0dbc1cfc82d7e92b42bcf874c47c66a533cf8ed4b6cb6ec3bba",
    }
    for source_id, digest in expected.items():
        assert sources[source_id]["hash"] == digest


def test_crew_document() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    source = sources["POL-CREW-055"]
    assert source["type"] == "regulation"
    assert source["priority"] == "P1"
    assert source["hash"] == "2c316eb3171f388de2bb340ee3b5d1b815eaea606cf529f909ab11cdffe28e17"
    assert source["status"] == "acquired"
    assert source["jurisdiction"] == "national"
    assert source["license"] == "public"
    assert source["location"] == "raw/POL-CREW-055/"
    assert "附件4" in source["notes"]


def test_source_watch_config() -> None:
    data = load_yaml("configs/source-watch.yaml")
    assert data["schema_version"] == 1
    assert set(data["authority_tiers"]) == {"A", "B", "C"}
    sources = data["sources"]
    assert len(sources) >= 8
    ids = {entry["id"] for entry in sources}
    assert len(ids) == len(sources)
    for entry in sources:
        assert entry["id"]
        assert entry["url"].startswith(("http://", "https://"))
        assert entry["authority"] in {"A", "B", "C"}
        assert entry["publisher"]
        assert entry["status"] in {"unchecked", "ok", "changed", "unbaselined", "unreachable"}


def test_source_class_and_currency() -> None:
    data = load_yaml("configs/corpus.yaml")
    classes = {"normative", "official_statistics", "standard", "reference"}
    bases = {"publication", "edition", "announcement", "retrieval"}
    cadence_by_class = {
        "normative": "monthly",
        "standard": "quarterly",
        "official_statistics": "annual",
        "reference": "semiannual",
    }
    for source in data["sources"]:
        assert "validity" not in source, source["id"]
        assert source["source_class"] in classes, source["id"]
        currency = source["currency"]
        assert currency["basis"] in bases, source["id"]
        assert currency["review_due"] >= currency["as_of"], source["id"]
        assert currency["cadence"] == cadence_by_class[source["source_class"]], source["id"]


def test_national_eval_section() -> None:
    config = load_yaml("configs/eval.yaml")
    entries = config["national"]
    assert [item["id"] for item in entries] == ["J4", "J5"]
    assert entries[0]["docs"] == ["POL-ENF-068"]
    assert entries[1]["docs"] == ["STD-YY-071"]


def test_registry_schema_v3() -> None:
    from scs_fkb.registry import CADENCES, load_registry

    registry = load_registry("configs/corpus.yaml")
    assert len(registry) == 99
    assert sum(1 for entry in registry.values() if entry["status"] == "acquired") == 99
    for entry in registry.values():
        assert entry["lifecycle"] in {"active", "retired"}
        assert entry["currency"]["cadence"] in CADENCES
        if entry["lifecycle"] == "retired":
            assert entry["retirement"]["decision_key"]


def test_schema_source_allowlists_match_registry() -> None:
    from scs_fkb.registry import CADENCE_CAPS, CADENCES, LICENSES, SENSITIVITIES

    source_schema = load_yaml("configs/schema.yaml")["source"]
    assert set(source_schema["licenses"]) == LICENSES
    assert set(source_schema["sensitivities"]) == SENSITIVITIES
    assert set(source_schema["cadences"]) == CADENCES
    assert source_schema["cadence_caps_days"] == CADENCE_CAPS


def test_candidate_register_is_valid() -> None:
    from scs_fkb.candidates import load_candidates
    from scs_fkb.registry import load_registry

    candidates = load_candidates("configs/candidates.yaml")
    assert len(candidates) == 15
    assert sum(1 for candidate in candidates if candidate["status"] == "accepted") == 14
    assert sum(1 for candidate in candidates if candidate["status"] == "open") == 1
    registry = load_registry("configs/corpus.yaml")
    accepted = [candidate for candidate in candidates if candidate["status"] == "accepted"]
    assert all(candidate["source_id"] in registry for candidate in accepted)


def test_cleanup_state() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    assert "DICT-GFW-047" not in registry
    for source_id in (
        "STD-MUR-045",
        "STD-OLCI-046",
        "DICT-GFW-048",
        "STD-CMEMS-049",
        "STD-HY1-056",
        "STD-ASFIS-044",
    ):
        assert source_id not in registry
    assert registry["STD-CWP-043"]["level"] == "international"


def test_environment_layer() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    for source_id in ("POL-OBS-072", "STAT-ECO-073", "STAT-DIS-074"):
        source = sources[source_id]
        assert source["level"] == "national"
        assert source["jurisdiction"] == "national"
        assert source["source_class"] in {"normative", "official_statistics"}
    assert sources["STAT-ECO-073"]["retrieval"]["parseable"] is True
    assert sources["STAT-DIS-074"]["retrieval"]["parseable"] is False
    collections = load_yaml("configs/reference-collections.yaml")["collections"]
    assert len(collections["policy"]["documents"]) == 30
    assert "海洋灾害" in collections["policy"]["cues"]


def test_species_layer() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    assert sources["POL-RES-075"]["retrieval"]["parseable"] is True
    assert sources["POL-RES-075"]["source_class"] == "normative"
    assert sources["STD-SPEC-076"]["retrieval"]["parseable"] is False
    assert sources["STD-SPEC-076"]["source_class"] == "normative"
    cues = load_yaml("configs/reference-collections.yaml")["collections"]["policy"]["cues"]
    assert {"物种", "保护", "名录", "放流", "增殖", "种质"} <= set(cues)


def test_port_layer() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    for source_id in ("POL-PORT-077",):
        assert sources[source_id]["retrieval"]["parseable"] is True
        assert sources[source_id]["source_class"] == "normative"
    cues = load_yaml("configs/reference-collections.yaml")["collections"]["policy"]["cues"]
    assert {"渔港", "锚地", "避风", "泊位", "靠泊"} <= set(cues)


def test_new_national_documents_are_indexed() -> None:
    pipeline = load_yaml("configs/pipeline.yaml")
    documents = set(pipeline["documents"])
    assert {
        "POL-ENF-068",
        "POL-OBS-072",
        "POL-RES-075",
        "POL-PORT-077",
        "POL-PEN-078",
        "POL-PEN-080",
        "POL-LIST-079",
        "POL-WATCH-082",
    } <= documents
    assert "STAT-ECO-073" not in documents
    assert "STAT-DIS-074" not in documents


def test_watch_has_the_new_national_pages() -> None:
    data = load_yaml("configs/source-watch.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    assert len(sources) >= 16
    expected = {
        "WATCH-MOJ-OBSERVATION",
        "WATCH-GOV-RES-075",
        "WATCH-GOV-PORT-077",
        "WATCH-NMHMS-BULLETINS",
        "WATCH-FORESTRY-SPECIES",
        "WATCH-YZB-PORTS",
    }
    assert expected <= set(sources)
    for source in sources.values():
        if source.get("status") == "ok":
            assert re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", ""))


def test_enforcement_layer() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    for source_id in ("POL-PEN-078", "POL-LIST-079"):
        assert sources[source_id]["retrieval"]["parseable"] is True
        assert sources[source_id]["source_class"] in {"normative", "standard"}
    crew = sources["POL-CREW-055"]["currency"]
    assert "No. 950" in crew["note"]
    cues = load_yaml("configs/reference-collections.yaml")["collections"]["policy"]["cues"]
    assert {"处罚", "罚款", "违法", "目录"} <= set(cues)


def test_penalty_cross_checks() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    for source_id in ("POL-RES-075", "POL-PEN-078"):
        assert "No. 950" in sources[source_id]["currency"]["note"]
    assert sources["POL-PEN-080"]["source_class"] == "normative"
    assert sources["POL-PEN-080"]["retrieval"]["parseable"] is True


def test_cleanup_080_state() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    assert "POL-PORT-078" not in registry
    for source_id in ("POL-ENF-068", "POL-OBS-072", "POL-RES-075", "POL-PORT-077"):
        assert registry[source_id]["retrieval"]["channel"] == "main"
    data_publications = {
        "STAT-CSY-027",
        "STAT-YB-2018",
        "STAT-YB-2019",
        "STAT-YB-2020",
        "STAT-YB-2021",
        "STAT-YB-2022",
        "STAT-YB-2023",
        "STAT-YB-2024",
        "STAT-YB-2025",
        "STAT-YB-2026",
        "DICT-STAT-013",
    }
    for source_id in data_publications:
        assert registry[source_id]["source_class"] in {"official_statistics", "reference"}


def test_watch_coverage_is_complete() -> None:
    from scs_fkb.registry import load_registry, validate_watch_coverage

    registry = load_registry("configs/corpus.yaml")
    watch = load_yaml("configs/source-watch.yaml")["sources"]
    validate_watch_coverage(registry, watch)
    ids = {entry["id"] for entry in watch}
    for source_id in (
        "WATCH-MOA-GAZETTE-2025",
        "WATCH-MOA-GAZETTE-202505",
        "WATCH-MOA-GAZETTE-202504",
        "WATCH-MOA-GAZETTE-202506",
        "WATCH-GD-ANNOUNCE-2020",
        "WATCH-GD-ANNOUNCE-2021",
        "WATCH-GD-NOTICES",
        "WATCH-GD-POLICY",
        "WATCH-HN-HULL-2019",
        "WATCH-NFTEC-MONITOR",
    ):
        assert source_id in ids
    for entry in watch:
        assert entry.get("status") == "ok" or "unreachable" in str(entry.get("note", "")).lower()
        if entry.get("status") == "ok":
            assert re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", ""))


def test_climate_closure_record() -> None:
    watch = load_yaml("configs/source-watch.yaml")["sources"]
    ids = {entry["id"] for entry in watch}
    assert {"WATCH-CMA-RULES", "WATCH-MNR-EMERGENCY"} <= ids
    text = Path("docs/corpus.md").read_text(encoding="utf-8")
    assert "## 5r. Climate and hazard" in text


def test_operations_resource_layer() -> None:
    data = load_yaml("configs/corpus.yaml")
    sources = {source["id"]: source for source in data["sources"]}
    for source_id in ("POL-WATCH-082",):
        assert sources[source_id]["retrieval"]["parseable"] is True
        assert sources[source_id]["source_class"] == "standard"
    assert "No. 950" in sources["POL-WATCH-082"]["currency"]["note"]
    cues = load_yaml("configs/reference-collections.yaml")["collections"]["policy"]["cues"]
    assert {"值班", "航行", "安全"} <= set(cues)


def test_pipeline_documents_report_the_main_channel() -> None:
    from scs_fkb.registry import load_registry

    pipeline = load_yaml("configs/pipeline.yaml")["documents"]
    registry = load_registry("configs/corpus.yaml")
    for doc_id in pipeline:
        assert registry[doc_id]["retrieval"]["channel"] == "main"


def test_provincial_entries_carry_currency() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    provincial = [
        "POL-HN-058",
        "POL-HN-059",
        "POL-GX-060",
        "POL-FJ-063",
        "STD-FJ-064",
        "STD-FJ-065",
        "STD-FJ-066",
        "STD-GD-064",
        "STD-GD-065",
        "STD-HN-066",
        "STD-HN-067",
    ]
    for source_id in provincial:
        entry = registry[source_id]
        assert entry["source_class"] in {"normative", "standard"}
        assert entry["currency"]["review_due"] >= entry["currency"]["as_of"]


def test_out_of_scope_material_is_removed() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    assert "POL-BREED-084" not in registry
    assert "POL-RANCH-083" not in registry
    assert "POL-RANCH-083" not in load_yaml("configs/pipeline.yaml")["documents"]
    cues = load_yaml("configs/reference-collections.yaml")["collections"]["policy"]["cues"]
    assert not {"海洋牧场", "示范区", "繁育", "水生野生动物"} & set(cues)
    assert {"值班", "航行", "安全"} <= set(cues)


def test_out_of_scope_titles_are_allowlisted() -> None:
    import re

    from scs_fkb.registry import load_registry

    banned = re.compile(r"养殖|繁育|海洋牧场|加工|饲料|病害|淡水|内陆|内河")
    allowlist = {"POL-RULE-020", "POL-RES-075"}
    registry = load_registry("configs/corpus.yaml")
    for source_id, entry in registry.items():
        if entry.get("lifecycle") != "active":
            continue
        title = f"{entry.get('title') or ''} {entry.get('title_zh') or ''}"
        if banned.search(title):
            assert source_id in allowlist, f"{source_id} carries an out-of-scope term: {title}"


def test_bulletins_removed() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    pipeline = load_yaml("configs/pipeline.yaml")["documents"]
    for source_id in (
        "STAT-BULL-025",
        "STAT-BULL-028",
        "STAT-BULL-029",
        "STAT-BULL-030",
        "STAT-BULL-031",
        "STAT-BULL-032",
    ):
        assert source_id not in registry
        assert source_id not in pipeline
    yearbooks = [s for s in registry.values() if s["type"] == "statistical_yearbook"]
    assert len(yearbooks) == 10


def test_currency_review_dates() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    assert not [entry for entry in registry.values() if "validity" in entry]
    for source_id, entry in registry.items():
        currency = entry["currency"]
        assert currency["review_due"] >= currency["as_of"], source_id


def test_vms_measure_is_closed_with_its_clause() -> None:
    from scs_fkb.registry import load_registry

    registry = load_registry("configs/corpus.yaml")
    currency = registry["POL-VMS-053"]["currency"]
    assert "Article 32" in currency["note"] or "2020年1月1日" in currency["note"]


def test_web_cards_registry() -> None:
    cards = load_yaml("configs/web-cards.yaml")["cards"]
    original = {
        "WEB-WORMS-LARIMICHTHYS-CROCEA",
        "WEB-WORMS-TRICHIURUS-LEPTURUS",
        "WEB-WORMS-DECAPTERUS-MARUADSI",
        "WEB-WORMS-FENNEROPENAEUS-CHINENSIS",
        "WEB-FAO-ISSCFG-GEAR",
        "WEB-GOV-CMA-WARNING-2007",
        "WEB-NASA-OCEANCOLOR",
        "WEB-EUMETSAT-SENTINEL3",
    }
    ids = {card["id"] for card in cards}
    assert original <= ids
    assert len(cards) >= 100
    for card in cards:
        assert card["url"].startswith("https://")
        assert card["source_class"] == "reference"
        if card["status"] == "ok":
            assert len(card["sha256"]) == 64
            assert card["excerpt"]
        else:
            assert card["status"] == "failed"


def test_retrieval_parameters_are_the_reviewed_set() -> None:
    retrieval = load_yaml("configs/pipeline.yaml")["retrieval"]
    assert retrieval["title_boost"] == 1.0
    assert retrieval["bm25_weight"] == 2.0
    assert retrieval["dense_weight"] == 1.0
    assert retrieval["fusion_k"] == 60


def test_eval_question_refinement_keeps_the_anchor() -> None:
    questions = Path("docs/questions.md").read_text(encoding="utf-8")
    assert "申请海洋渔业捕捞许可证应当提交哪些资料？" in questions
    anchors = load_yaml("configs/eval.yaml")["anchors"]["Q-M10"]
    assert anchors[0]["doc"] == "POL-STD-010"
    assert anchors[0]["section"] == "第二十八条"


def test_closure_date_synonym_is_active() -> None:
    groups = load_yaml("configs/lexicon.yaml")["groups"]
    assert any(group["term"] == "起止日期" and "休渔时间" in group["variants"] for group in groups)


def test_eval_gold_covers_scored_questions() -> None:
    config = load_yaml("configs/eval.yaml")
    gold = config["gold"]
    scored = set(config["anchors"]) | set(config["abstention"])
    scored |= {item["id"] for item in config["reference"]}
    scored |= {item["id"] for item in config["statistics"]}
    assert scored <= set(gold)
    for question_id, entry in gold.items():
        assert question_id.startswith("Q-")
        if entry.get("abstain") or entry.get("deferred"):
            continue
        assert entry.get("points"), question_id
        assert entry.get("evidence"), question_id
