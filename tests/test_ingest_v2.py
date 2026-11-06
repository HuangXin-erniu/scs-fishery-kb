from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scs_fkb.ingest_v2 import SnapshotError, build_v2, loaders, snapshot_registry
from scs_fkb.ingest_v2.chunking import hierarchical_chunks
from scs_fkb.ingest_v2.loaders import load_document, loader_plan
from scs_fkb.models import Document
from scs_fkb.parsers import Page
from scs_fkb.registry import RegistryError


def _html(*articles: str) -> str:
    body = "".join(f"<p>{article}</p>" for article in articles)
    return f"<html><body>{body}</body></html>"


def _source(
    source_id: str,
    root: Path,
    *,
    content: str | None = None,
    fmt: str = "html",
    location: str | None = None,
) -> dict:
    directory = root / "raw" / source_id
    directory.mkdir(parents=True, exist_ok=True)
    if fmt == "html":
        path = directory / "doc.html"
        path.write_text(
            content or _html("第一条 总则内容说明与适用范围。", "第二条 管理要求与办理流程。"),
            encoding="utf-8",
        )
    else:
        path = directory / "doc.bin"
        path.write_text("not a real document", encoding="utf-8")
    relative = location or f"raw/{source_id}/{path.name}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "id": source_id,
        "title": f"Test {source_id}",
        "title_zh": f"测试 {source_id}",
        "publisher": "测试机关",
        "year": 2026,
        "type": "notice",
        "jurisdiction": "national",
        "format": fmt,
        "location": relative,
        "license": "public",
        "sensitivity": "public",
        "status": "acquired",
        "hash": digest,
        "level": "national",
        "authority_tier": "A",
        "source_class": "normative",
        "currency": {
            "as_of": "2026-11-06",
            "basis": "publication",
            "review_due": "2026-12-06",
            "cadence": "monthly",
        },
        "retrieval": {"channel": "main", "parseable": True, "note": "test"},
        "lifecycle": "active",
    }


def _write(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _corpus(tmp_path: Path, sources: list[dict]) -> Path:
    return _write(
        tmp_path / "corpus.yaml",
        {"schema_version": 1, "source_record_schema": 4, "sources": sources},
    )


def _pipeline(tmp_path: Path, documents: list[str]) -> Path:
    return _write(
        tmp_path / "pipeline.yaml",
        {"schema_version": 1, "documents": documents, "chunking": {"max_fallback_chars": 800}},
    )


def test_snapshot_and_build_produce_parents_and_children(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    source = _source("POL-T-001", root)
    config = _corpus(tmp_path, [source])
    pipeline = _pipeline(tmp_path, ["POL-T-001"])

    result = build_v2(config, pipeline, root)

    assert result.documents == 1
    assert result.children > 0
    assert result.parents > 0
    assert result.quarantined == []
    manifest = json.loads((root / "v2/processed/manifest.json").read_text(encoding="utf-8"))
    assert manifest["per_document"]["POL-T-001"]["parser"] == "html.v1"
    assert (root / "v2/snapshots.json").is_file()
    children = [
        json.loads(line)
        for line in (root / "v2/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    parents = [
        json.loads(line)
        for line in (root / "v2/processed/parents.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {child["section"] for child in children} == {"第一条", "第二条"}
    assert all(child["parent_id"] for child in children)
    parent_ids = {parent["chunk_id"] for parent in parents}
    assert {child["parent_id"] for child in children} <= parent_ids
    assert all(parent["chunk_type"] == "parent" for parent in parents)
    assert all(child["chunk_type"] == "text" for child in children)


def test_second_build_skips_unchanged_document(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    source = _source("POL-T-001", root)
    config = _corpus(tmp_path, [source])
    pipeline = _pipeline(tmp_path, ["POL-T-001"])

    first = build_v2(config, pipeline, root)
    second = build_v2(config, pipeline, root)

    assert first.rebuilt == ["POL-T-001"]
    assert second.rebuilt == []
    assert second.skipped == ["POL-T-001"]
    assert second.chunks == first.chunks


def test_changed_source_rebuilds_only_that_document(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    source = _source("POL-T-001", root)
    config = _corpus(tmp_path, [source])
    pipeline = _pipeline(tmp_path, ["POL-T-001"])
    build_v2(config, pipeline, root)

    source = _source(
        "POL-T-001",
        root,
        content=_html(
            "第一条 总则内容说明与适用范围。",
            "第二条 管理要求与办理流程。",
            "第三条 新增要求与执行时间。",
        ),
    )
    _corpus(tmp_path, [source])
    result = build_v2(config, pipeline, root)

    assert result.rebuilt == ["POL-T-001"]
    assert result.skipped == []
    assert result.counts["POL-T-001"] == 3


def test_removed_document_drops_records(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    first = _source("POL-T-001", root)
    second = _source("POL-T-002", root)
    config = _corpus(tmp_path, [first, second])
    pipeline = _pipeline(tmp_path, ["POL-T-001", "POL-T-002"])
    build_v2(config, pipeline, root)

    pipeline = _pipeline(tmp_path, ["POL-T-001"])
    result = build_v2(config, pipeline, root)

    assert result.removed == ["POL-T-002"]
    assert "POL-T-002" not in result.counts
    assert result.documents == 1


def test_parse_failure_is_quarantined(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    source = _source("POL-T-001", root, fmt="unknown")
    config = _corpus(tmp_path, [source])
    pipeline = _pipeline(tmp_path, ["POL-T-001"])

    result = build_v2(config, pipeline, root)

    assert result.documents == 0
    assert result.quarantined
    assert result.quarantined[0]["doc_id"] == "POL-T-001"


def test_data_root_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text(_html("第一条 外部内容。"), encoding="utf-8")
    source = _source("POL-T-001", root, location="../outside.html")
    config = _corpus(tmp_path, [source])

    with pytest.raises((SnapshotError, RegistryError), match="data root"):
        build_v2(config, _pipeline(tmp_path, ["POL-T-001"]), root)


def test_directory_snapshot_records_a_file_manifest(tmp_path: Path) -> None:
    root = tmp_path / "data"
    directory = root / "raw" / "STAT-DIR-001"
    directory.mkdir(parents=True)
    (directory / "a.xlsx").write_text("a", encoding="utf-8")
    (directory / "b.xlsx").write_text("b", encoding="utf-8")
    source = _source("STAT-DIR-001", root)
    (directory / "doc.html").unlink()
    source.update(
        {
            "format": "xlsx",
            "location": "raw/STAT-DIR-001/",
            "hash": "a" * 64,
            "type": "statistical_yearbook",
            "license": "internal",
            "sensitivity": "internal",
        }
    )
    manifest = snapshot_registry({"STAT-DIR-001": source}, root)
    metadata = manifest["sources"]["STAT-DIR-001"]
    assert metadata["kind"] == "directory"
    assert metadata["verified"] is False
    assert len(metadata["files"]) == 2
    assert metadata["tree_sha256"]


def test_loader_plan_and_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert loader_plan("html", "corpus") == ["legacy"]
    assert loader_plan("pdf", "corpus") == ["legacy", "docling"]
    assert loader_plan("html", "web") == ["trafilatura", "legacy"]
    assert loader_plan("unknown", "corpus") == ["legacy"]

    path = tmp_path / "page.html"
    path.write_text(_html("第一条 网页正文。"), encoding="utf-8")
    monkeypatch.setattr(loaders, "available", lambda name: False)
    result = load_document(path, "html", source_kind="web")
    assert result.parser == "html.v1"
    assert result.fallback is True


def test_parent_child_anchors_match_the_base_chunker(tmp_path: Path) -> None:
    document = Document(
        doc_id="POL-T-001",
        source_id="POL-T-001",
        title="Test",
        title_zh="测试",
        publisher="测试机关",
        year=2026,
        doc_type="notice",
        sensitivity="public",
        language="zh",
        page_count=1,
        file_hash="a" * 64,
        authority_tier="A",
        source_class="normative",
        level="national",
    )
    pages = [
        Page(number=0, lines=["第一条 总则内容说明与适用范围。", "第二条 管理要求与办理流程。"])
    ]
    hierarchy = hierarchical_chunks(document, pages)
    assert [child.section for child in hierarchy.children] == ["第一条", "第二条"]
    assert hierarchy.children[0].parent_id == hierarchy.parents[0].chunk_id
    assert hierarchy.children[0].trust == "authoritative"
