from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
import yaml

from scs_fkb.reference import ReferenceError, load_collections, lookup

PRODUCT = "Sea surface temperature analysis with chlorophyll ocean colour resolution anomaly."
POLICY = "统计资料应当定期公布，并与有关部门共享。年报统计资料于翌年发布。"


def _root(tmp_path: Path) -> Path:
    (tmp_path / "raw" / "DOC-A").mkdir(parents=True)
    (tmp_path / "raw" / "DOC-B").mkdir(parents=True)
    (tmp_path / "raw" / "DOC-A" / "a.html").write_text(
        f"<html><body><p>{PRODUCT}</p></body></html>", encoding="utf-8"
    )
    (tmp_path / "raw" / "DOC-B" / "b.html").write_text(
        f"<html><body><p>{POLICY}</p></body></html>", encoding="utf-8"
    )
    return tmp_path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config(root: Path, *, corrupt: bool = False) -> Path:
    data = {
        "schema_version": 1,
        "collections": {
            "product": {
                "concepts": ["sea surface temperature", "chlorophyll", "resolution", "anomaly"],
                "documents": [
                    {
                        "id": "DOC-A",
                        "title": "A",
                        "file": "raw/DOC-A/a.html",
                        "sha256": "0" * 64 if corrupt else _sha(root / "raw" / "DOC-A" / "a.html"),
                        "license": "public",
                        "language": "en",
                    }
                ],
            },
            "policy": {
                "cues": ["统计", "公布"],
                "documents": [
                    {
                        "id": "DOC-B",
                        "title": "B",
                        "file": "raw/DOC-B/b.html",
                        "sha256": _sha(root / "raw" / "DOC-B" / "b.html"),
                        "license": "public",
                        "language": "zh",
                    }
                ],
            },
        },
    }
    path = root / "collections.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_load_collections(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root)
    collections = load_collections(config)
    assert set(collections) == {"product", "policy"}


def test_product_lookup_uses_concepts(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root)
    hits = lookup(
        "海表温度与叶绿素的时空分辨率如何解读？",
        root=root,
        collections_path=config,
        collection="product",
    )
    assert [hit.chunk.doc_id for hit in hits] == ["DOC-A"]


def test_product_lookup_ignores_questions_without_concepts(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root)
    assert (
        lookup("伏季休渔的起止时间", root=root, collections_path=config, collection="product") == []
    )


def test_product_lookup_reaches_chinese_documents(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "raw" / "DOC-C").mkdir(parents=True)
    (root / "raw" / "DOC-C" / "c.html").write_text(
        "<html><body><p>海洋水色水温扫描仪覆盖周期：1天（单颗卫星）。</p></body></html>",
        encoding="utf-8",
    )
    data = {
        "schema_version": 1,
        "collections": {
            "product": {
                "concepts": ["ocean colour", "coverage cycle", "resolution"],
                "documents": [
                    {
                        "id": "DOC-C",
                        "title": "C",
                        "file": "raw/DOC-C/c.html",
                        "sha256": _sha(root / "raw" / "DOC-C" / "c.html"),
                        "license": "public",
                        "language": "zh",
                    }
                ],
            },
            "policy": {
                "cues": ["统计"],
                "documents": [
                    {
                        "id": "DOC-B",
                        "title": "B",
                        "file": "raw/DOC-B/b.html",
                        "sha256": _sha(root / "raw" / "DOC-B" / "b.html"),
                        "license": "public",
                        "language": "zh",
                    }
                ],
            },
        },
    }
    config = tmp_path / "chinese-collections.yaml"
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    hits = lookup(
        "海洋水色产品的覆盖周期与分辨率是多少？",
        root=root,
        collections_path=config,
        collection="product",
    )
    assert [hit.chunk.doc_id for hit in hits] == ["DOC-C"]
    assert "覆盖周期" in hits[0].chunk.text


def test_policy_lookup_requires_a_cue(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root)
    assert (
        lookup("伏季休渔的起止时间", root=root, collections_path=config, collection="policy") == []
    )
    hits = lookup("统计资料如何公布？", root=root, collections_path=config, collection="policy")
    assert [hit.chunk.doc_id for hit in hits] == ["DOC-B"]


def test_hash_mismatch_raises(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root, corrupt=True)
    with pytest.raises(ReferenceError, match="hash mismatch"):
        lookup("海表温度", root=root, collections_path=config, collection="product")


def test_unknown_collection_raises(tmp_path: Path) -> None:
    root = _root(tmp_path)
    config = _config(root)
    with pytest.raises(ReferenceError, match="unknown reference collection"):
        lookup("海表温度", root=root, collections_path=config, collection="magic")


DOCX_BODY = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body><w:p><w:r><w:t>统计资料应当定期公布，并与有关部门共享。</w:t></w:r></w:p></w:body>"
    "</w:document>"
)


def test_collection_dispatches_docx(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "raw" / "DOC-D").mkdir(parents=True)
    path = root / "raw" / "DOC-D" / "d.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", DOCX_BODY)
    data = {
        "schema_version": 1,
        "collections": {
            "policy": {
                "cues": ["统计"],
                "documents": [
                    {
                        "id": "DOC-D",
                        "title": "D",
                        "file": "raw/DOC-D/d.docx",
                        "sha256": _sha(path),
                        "license": "public",
                        "language": "zh",
                    }
                ],
            }
        },
    }
    config = tmp_path / "docx-collections.yaml"
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    hits = lookup("统计资料如何公布？", root=root, collections_path=config, collection="policy")
    assert [hit.chunk.doc_id for hit in hits] == ["DOC-D"]
    assert "统计资料" in hits[0].chunk.text
