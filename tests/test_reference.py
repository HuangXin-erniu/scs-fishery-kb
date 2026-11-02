from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
import yaml

from scs_fkb.models import Chunk, SearchHit
from scs_fkb.reference import ReferenceError, diverse_hits, load_collections, lookup

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


def _province_root(tmp_path: Path) -> Path:
    for doc_id, text in {
        "DOC-HN": "海南省 2026年休渔时间从5月1日12时至8月16日12时。",
        "DOC-GX": "广西 2026年休渔时间从5月1日12时起至8月16日12时止。",
        "DOC-GD": "广东省休渔管理要求，违规出海依法查处。",
    }.items():
        directory = tmp_path / "raw" / doc_id
        directory.mkdir(parents=True)
        (directory / "page.html").write_text(
            f"<html><body><p>{text}</p></body></html>", encoding="utf-8"
        )
    return tmp_path


def _province_config(root: Path, *, jurisdictions: bool = True) -> Path:
    documents = []
    for doc_id, code in (("DOC-HN", "hainan"), ("DOC-GX", "guangxi"), ("DOC-GD", "guangdong")):
        entry = {
            "id": doc_id,
            "title": doc_id,
            "file": f"raw/{doc_id}/page.html",
            "sha256": _sha(root / "raw" / doc_id / "page.html"),
            "license": "public",
            "language": "zh",
        }
        if jurisdictions:
            entry["jurisdiction"] = code
        documents.append(entry)
    data = {
        "schema_version": 1,
        "collections": {"policy": {"cues": ["休渔"], "documents": documents}},
    }
    path = root / ("jurisdictions.yaml" if jurisdictions else "plain.yaml")
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_policy_lookup_prefers_the_named_province(tmp_path: Path) -> None:
    root = _province_root(tmp_path)
    config = _province_config(root)
    hits = lookup(
        "海南省的休渔时间是什么？", root=root, collections_path=config, collection="policy"
    )
    assert hits[0].chunk.doc_id == "DOC-HN"
    hits = lookup("广西的休渔时间是什么？", root=root, collections_path=config, collection="policy")
    assert hits[0].chunk.doc_id == "DOC-GX"


def test_policy_lookup_without_a_province_keeps_the_score_order(tmp_path: Path) -> None:
    root = _province_root(tmp_path)
    with_j = _province_config(root)
    without_j = _province_config(root, jurisdictions=False)
    baseline = [
        hit.chunk.doc_id
        for hit in lookup(
            "休渔时间是什么？", root=root, collections_path=without_j, collection="policy"
        )
    ]
    ranked = [
        hit.chunk.doc_id
        for hit in lookup(
            "休渔时间是什么？", root=root, collections_path=with_j, collection="policy"
        )
    ]
    assert ranked == baseline


def test_policy_lookup_with_an_unknown_province_keeps_the_score_order(tmp_path: Path) -> None:
    root = _province_root(tmp_path)
    with_j = _province_config(root)
    without_j = _province_config(root, jurisdictions=False)
    baseline = [
        hit.chunk.doc_id
        for hit in lookup(
            "福建省的休渔时间是什么？", root=root, collections_path=without_j, collection="policy"
        )
    ]
    ranked = [
        hit.chunk.doc_id
        for hit in lookup(
            "福建省的休渔时间是什么？", root=root, collections_path=with_j, collection="policy"
        )
    ]
    assert ranked == baseline


def _passage(doc: str, section: str, text: str, score: float = 1.0) -> SearchHit:
    chunk = Chunk(
        chunk_id=f"{doc}-{section}",
        doc_id=doc,
        source_id=doc,
        page=0,
        section=section,
        text=text,
        token_count=1,
        char_start=0,
        char_end=len(text),
        sensitivity="public",
    )
    return SearchHit(chunk=chunk, score=score)


def test_diverse_hits_caps_one_document_and_fills_from_the_next() -> None:
    hits = [
        _passage("A", "一", "x"),
        _passage("A", "二", "y"),
        _passage("A", "三", "z"),
        _passage("B", "一", "w"),
    ]
    selected = diverse_hits(hits, per_doc=2, limit=3)
    assert [hit.chunk.doc_id for hit in selected] == ["A", "A", "B"]


def test_diverse_hits_drops_identical_passages() -> None:
    same = _passage("A", "一", "x")
    selected = diverse_hits([same, same], per_doc=2, limit=3)
    assert len(selected) == 1


def test_diverse_hits_keeps_a_short_single_document() -> None:
    hits = [_passage("A", "一", "x")]
    assert diverse_hits(hits) == hits


def _level_root(tmp_path: Path) -> Path:
    bodies = {
        "DOC-MUN": "休渔 休渔 休渔 休渔 休渔时间从5月1日12时至8月16日12时。",
        "DOC-PROV": "休渔 休渔 休渔时间从5月1日12时至8月16日12时。",
        "DOC-NAT": "休渔时间从5月1日12时至8月16日12时。",
        "DOC-NOLEVEL": "休渔时间从5月1日12时至8月16日12时。",
    }
    for doc_id, body in bodies.items():
        directory = tmp_path / "raw" / doc_id
        directory.mkdir(parents=True)
        (directory / "page.html").write_text(
            f"<html><body><p>{body}</p></body></html>", encoding="utf-8"
        )
    return tmp_path


def _level_config(root: Path, *, with_province: bool = True) -> Path:
    entries = [
        ("DOC-MUN", "municipal", ""),
        ("DOC-PROV", "provincial", "hainan" if with_province else ""),
        ("DOC-NAT", "national", ""),
        ("DOC-NOLEVEL", None, ""),
    ]
    documents = []
    for doc_id, level, jurisdiction in entries:
        entry = {
            "id": doc_id,
            "title": doc_id,
            "file": f"raw/{doc_id}/page.html",
            "sha256": _sha(root / "raw" / doc_id / "page.html"),
            "license": "public",
            "language": "zh",
        }
        if level:
            entry["level"] = level
        if jurisdiction:
            entry["jurisdiction"] = jurisdiction
        documents.append(entry)
    data = {
        "schema_version": 1,
        "collections": {"policy": {"cues": ["休渔"], "documents": documents}},
    }
    path = root / "levels.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_policy_lookup_puts_national_first_without_a_province(tmp_path: Path) -> None:
    root = _level_root(tmp_path)
    config = _level_config(root)
    hits = lookup(
        "休渔时间是什么？", top_k=4, root=root, collections_path=config, collection="policy"
    )
    ids = [hit.chunk.doc_id for hit in hits]
    assert ids[0] == "DOC-NAT"
    assert ids[1] == "DOC-PROV"
    assert ids[-1] == "DOC-MUN"


def test_policy_lookup_puts_the_named_province_before_national(tmp_path: Path) -> None:
    root = _level_root(tmp_path)
    config = _level_config(root)
    hits = lookup(
        "海南省的休渔时间是什么？", root=root, collections_path=config, collection="policy"
    )
    assert hits[0].chunk.doc_id == "DOC-PROV"
    assert hits[1].chunk.doc_id == "DOC-NAT"


def test_policy_lookup_treats_a_missing_level_as_provincial(tmp_path: Path) -> None:
    root = _level_root(tmp_path)
    config = _level_config(root)
    hits = lookup(
        "休渔时间是什么？", top_k=4, root=root, collections_path=config, collection="policy"
    )
    ids = [hit.chunk.doc_id for hit in hits]
    assert ids.index("DOC-NOLEVEL") < ids.index("DOC-MUN")
