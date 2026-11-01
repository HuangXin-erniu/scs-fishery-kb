from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scs_fkb.answer import answer_question, validate_citations
from scs_fkb.bm25 import BM25Index
from scs_fkb.chunking import chunk_document
from scs_fkb.corpus import CorpusError
from scs_fkb.ingest import IngestError, ingest
from scs_fkb.models import Chunk, Document, SearchHit
from scs_fkb.parsers.base import Page
from scs_fkb.parsers.html import extract_main_text
from scs_fkb.store import load_chunks
from scs_fkb.text import tokenize


def _document(doc_id: str = "TEST-001", sensitivity: str = "public") -> Document:
    return Document(
        doc_id=doc_id,
        source_id=doc_id,
        title="测试法规",
        title_zh="测试法规",
        publisher="测试机关",
        year=2026,
        doc_type="law",
        sensitivity=sensitivity,
        language="zh",
        page_count=1,
        file_hash="0" * 64,
    )


def _chunk(
    chunk_id: str,
    section: str,
    text: str,
    sensitivity: str = "public",
    page: int = 1,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="TEST-001",
        source_id="TEST-001",
        page=page,
        section=section,
        text=text,
        token_count=len(tokenize(text)),
        char_start=0,
        char_end=len(text),
        sensitivity=sensitivity,
    )


def _pages(text: str, number: int = 0) -> list[Page]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [Page(number=number, lines=lines)]


def test_tokenize_chinese_bigrams() -> None:
    tokens = tokenize("伏季休渔")
    assert "伏季" in tokens
    assert "休渔" in tokens


def test_extract_drops_navigation() -> None:
    html = """
    <html><body>
      <div>网站地图 首页</div>
      <p>第一条 为了加强渔业资源的保护，制定本法。</p>
      <p>第二条 在中华人民共和国内水从事养殖，适用本法。</p>
      <div>版权所有 某市政府</div>
    </body></html>
    """
    text = extract_main_text(html)
    assert "第一条" in text
    assert "第二条" in text
    assert "网站地图" not in text
    assert "版权所有" not in text


def test_extract_recovers_unclosed_paragraphs() -> None:
    html = "<p>第一条 为了保护渔业资源，制定本法。<p>第二条 本法适用于内水。"
    text = extract_main_text(html)
    assert "第一条" in text
    assert "第二条" in text


def test_chunk_law_by_article() -> None:
    text = "第一条 为了保护渔业资源，制定本法。\n继续说明。\n第二条 本法适用于内水。"
    chunks = chunk_document(_document(), _pages(text))
    assert [chunk.section for chunk in chunks] == ["第一条", "第二条"]
    assert "继续说明" in chunks[0].text


def test_chunk_notice_by_section() -> None:
    text = "一、休渔海域\n北纬12度以北的南海。\n二、休渔时间\n5月1日12时至8月16日12时。"
    chunks = chunk_document(_document(), _pages(text))
    assert [chunk.section for chunk in chunks] == ["一、休渔海域", "二、休渔时间"]


def test_chunk_keeps_page_numbers() -> None:
    pages = [
        Page(number=1, lines=["附件1 专项捕捞许可", "品种 省份 作业场所"]),
        Page(number=2, lines=["鱿鱼 广西 36艘 2500吨"]),
        Page(number=11, lines=["鱿鱼 海南 70艘 5000吨"]),
    ]
    chunks = chunk_document(_document(), pages)
    assert [chunk.page for chunk in chunks] == [1, 2, 11]
    assert chunks[0].chunk_id == "TEST-001-0000"
    assert chunks[2].chunk_id == "TEST-001-0002"


def test_bm25_ranks_relevant() -> None:
    chunks = [
        _chunk("c1", "一、休渔海域", "北纬12度以北的南海海域，5月1日12时至8月16日12时休渔。"),
        _chunk("c2", "第五条", "申请捕捞许可证应当提交渔业船舶检验证书。"),
        _chunk("c3", "第三十四条", "海洋大中型渔业船舶应当如实填写作业日志。"),
    ]
    hits = BM25Index(chunks).search("休渔 时间 南海", top_k=3)
    assert hits
    assert hits[0].chunk.chunk_id == "c1"


def test_bm25_sensitivity_filter() -> None:
    chunks = [
        _chunk("c1", "第一条", "公开休渔规定", sensitivity="public"),
        _chunk("c2", "第二条", "内部休渔规定", sensitivity="internal"),
    ]
    hits = BM25Index(chunks).search("休渔规定", top_k=5, sensitivity_ceiling="public")
    assert [hit.chunk.chunk_id for hit in hits] == ["c1"]


def test_answer_citations_resolve() -> None:
    chunk = _chunk(
        "c1",
        "第三十四条",
        "海洋大中型渔业船舶应当如实填写作业日志，记载捕捞作业、转载、购销等信息。",
    )
    answer = answer_question("作业日志应当记录什么", [SearchHit(chunk=chunk, score=1.5)])
    assert not answer.abstained
    assert "[TEST-001 p.1 §第三十四条]" in answer.text
    ok, invalid = validate_citations(answer.text, [SearchHit(chunk=chunk, score=1.5)])
    assert ok
    assert invalid == []


def test_answer_citation_without_page() -> None:
    chunk = _chunk(
        "c1",
        "第一条",
        "为了加强渔业资源的保护、增殖、开发和合理利用，制定本法。",
        page=0,
    )
    answer = answer_question("制定本法的目的是什么", [SearchHit(chunk=chunk, score=1.5)])
    assert not answer.abstained
    assert "[TEST-001 §第一条]" in answer.text
    ok, invalid = validate_citations(answer.text, [SearchHit(chunk=chunk, score=1.5)])
    assert ok
    assert invalid == []


def test_answer_prefers_certificate_sentence() -> None:
    chunk = _chunk(
        "c1",
        "第二十八条",
        "第二十八条 申请捕捞许可证，应当提交下列资料：\n"
        "（二）船舶所有人营业执照；\n"
        "（三）渔业船舶检验证书和所有权登记证书。",
    )
    answer = answer_question("申请捕捞许可证需要哪些证书", [SearchHit(chunk=chunk, score=2.0)])
    assert not answer.abstained
    assert "检验证书" in answer.text
    assert "营业执照" not in answer.text


def test_answer_prefers_date_range_for_time_question() -> None:
    implementation = _chunk("c1", "四、实施时间", "上述规定自2023年4月15日起施行。")
    closure = _chunk(
        "c2",
        "三、休渔时间",
        "（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。",
    )
    answer = answer_question(
        "南海区伏季休渔的起止时间是什么",
        [SearchHit(chunk=implementation, score=10.0), SearchHit(chunk=closure, score=8.0)],
        min_matched=0,
    )
    assert not answer.abstained
    assert "5月1日" in answer.text
    assert "2023年4月15日" not in answer.text


def test_answer_abstains_without_hits() -> None:
    answer = answer_question("今天天气怎么样", [])
    assert answer.abstained
    assert answer.reason == "no_evidence"


def test_answer_abstains_on_weak_match() -> None:
    chunk = _chunk("c1", "第一条", "为了加强渔业资源的保护，制定本法。")
    answer = answer_question("渔情通报里叶绿素浓度如何解读", [SearchHit(chunk=chunk, score=9.0)])
    assert answer.abstained
    assert answer.reason == "weak_evidence"


def test_answer_abstains_below_min_score() -> None:
    chunk = _chunk("c1", "第一条", "为了加强渔业资源的保护、增殖、开发和合理利用，制定本法。")
    answer = answer_question(
        "制定本法的目的是什么",
        [SearchHit(chunk=chunk, score=2.0)],
        min_score=6.0,
    )
    assert answer.abstained
    assert answer.reason == "weak_evidence"


def test_invalid_citation_rejected() -> None:
    chunk = _chunk("c1", "第三十四条", "作业日志要求。")
    ok, invalid = validate_citations("[TEST-001 p.1 §不存在]", [SearchHit(chunk=chunk, score=1.0)])
    assert not ok
    assert invalid


def _write_minimal_corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    data_root = tmp_path / "data"
    raw = data_root / "raw" / "TEST-001"
    raw.mkdir(parents=True)
    html = (
        "<html><body><div>网站地图</div>"
        "<p>第一条 为了保护渔业资源，制定本法。</p>"
        "<p>第二条 本法适用于内水。</p>"
        "<div>版权所有</div></body></html>"
    )
    source_file = raw / "doc.html"
    source_file.write_text(html, encoding="utf-8")
    digest = hashlib.sha256(source_file.read_bytes()).hexdigest()
    config = {
        "schema_version": 1,
        "sources": [
            {
                "id": "TEST-001",
                "category": "policy_standards",
                "title": "测试法规",
                "title_zh": "测试法规",
                "publisher": "测试机关",
                "year": 2026,
                "type": "law",
                "format": "html",
                "location": "raw/TEST-001/doc.html",
                "license": "public",
                "sensitivity": "public",
                "status": "acquired",
                "hash": digest,
            }
        ],
    }
    config_path = tmp_path / "corpus.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    pipeline = {
        "schema_version": 1,
        "documents": ["TEST-001"],
        "chunking": {"max_fallback_chars": 800},
    }
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(yaml.safe_dump(pipeline, allow_unicode=True), encoding="utf-8")
    return config_path, pipeline_path, data_root


def test_ingest_writes_outputs(tmp_path: Path) -> None:
    config_path, pipeline_path, data_root = _write_minimal_corpus(tmp_path)

    summary = ingest(config_path, pipeline_path, data_root)
    assert summary["documents"] == 1
    assert summary["chunks"] == 2
    assert summary["parsers"] == {"TEST-001": "html.v1"}

    chunks, manifest = load_chunks(data_root)
    assert len(chunks) == 2
    assert manifest["counts"] == {"TEST-001": 2}
    assert manifest["pages"] == {"TEST-001": 1}
    assert all("网站地图" not in chunk.text for chunk in chunks)
    assert all("版权所有" not in chunk.text for chunk in chunks)


def test_ingest_is_reproducible(tmp_path: Path) -> None:
    config_path, pipeline_path, data_root = _write_minimal_corpus(tmp_path)
    first = ingest(config_path, pipeline_path, data_root)
    second = ingest(config_path, pipeline_path, data_root)
    assert first["index_version"] == second["index_version"]
    assert first["counts"] == second["counts"]


def test_ingest_rejects_changed_source(tmp_path: Path) -> None:
    config_path, pipeline_path, data_root = _write_minimal_corpus(tmp_path)
    source_file = data_root / "raw" / "TEST-001" / "doc.html"
    source_file.write_text("<p>第一条 被篡改。 </p>", encoding="utf-8")
    with pytest.raises(CorpusError, match="source.hash_mismatch"):
        ingest(config_path, pipeline_path, data_root)


def test_ingest_rejects_unknown_document(tmp_path: Path) -> None:
    config_path, pipeline_path, data_root = _write_minimal_corpus(tmp_path)
    pipeline_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "documents": ["MISSING-001"],
                "chunking": {"max_fallback_chars": 800},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(IngestError, match="source.missing"):
        ingest(config_path, pipeline_path, data_root)


def test_chunking_drops_table_of_contents_lines() -> None:
    text = (
        "一、渔港的主要功能和重要作用.......... 1\n我国是海洋大国。\n二、沿海渔港建设情况...... 2"
    )
    chunks = chunk_document(_document(), _pages(text))
    assert all("......" not in chunk.text for chunk in chunks)
    assert all(".........." not in chunk.section for chunk in chunks)


def test_chunking_skips_tiny_fragments() -> None:
    pages = [
        Page(number=0, lines=["目 录\nI"]),
        Page(number=0, lines=["第一条 为了加强渔业资源的保护，制定本法。"]),
    ]
    chunks = chunk_document(_document(), pages)
    assert [chunk.section for chunk in chunks] == ["第一条"]


def test_ingest_rejects_duplicate_documents(tmp_path: Path) -> None:
    config_path, pipeline_path, data_root = _write_minimal_corpus(tmp_path)
    pipeline_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "documents": ["TEST-001", "TEST-001"],
                "chunking": {"max_fallback_chars": 800},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(IngestError, match="unique"):
        ingest(config_path, pipeline_path, data_root)
