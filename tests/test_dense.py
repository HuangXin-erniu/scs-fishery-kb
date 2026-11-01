from __future__ import annotations

from pathlib import Path

import pytest

from scs_fkb.dense import DenseError, DenseIndex, index_path
from scs_fkb.embed import HashingEncoder
from scs_fkb.models import Chunk


def _chunk(chunk_id: str, text: str, sensitivity: str = "public") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id="DOC-" + chunk_id.upper(),
        source_id="DOC-" + chunk_id.upper(),
        page=1,
        section="第一条",
        text=text,
        token_count=len(text),
        char_start=0,
        char_end=len(text),
        sensitivity=sensitivity,
    )


def test_hashing_encoder_is_deterministic() -> None:
    encoder = HashingEncoder(dim=32)
    first = encoder.embed_passages(["休渔期管理"])
    second = encoder.embed_passages(["休渔期管理"])
    assert first == second
    assert len(first[0]) == 32
    assert abs(sum(value * value for value in first[0]) - 1.0) < 1e-9


def test_build_and_search() -> None:
    chunks = [_chunk("a", "休渔期违规作业的处罚依据"), _chunk("b", "捕捞许可证申请材料")]
    index = DenseIndex.build(chunks, HashingEncoder(dim=64), "v1")
    hits = index.search(HashingEncoder(dim=64).embed_query("休渔期违规作业的处罚依据"), top_k=2)
    assert hits[0].chunk.chunk_id == "a"
    assert hits[0].score > 0


def test_sensitivity_filter() -> None:
    chunks = [_chunk("a", "公开休渔规定"), _chunk("b", "内部休渔规定", sensitivity="internal")]
    index = DenseIndex.build(chunks, HashingEncoder(dim=64), "v1")
    hits = index.search(HashingEncoder(dim=64).embed_query("休渔规定"), top_k=5)
    assert [hit.chunk.chunk_id for hit in hits] == ["a"]


def test_text_attachment() -> None:
    chunks = [_chunk("a", "休渔期管理")]
    index = DenseIndex.build(chunks, HashingEncoder(dim=64), "v1")
    hits = index.search(
        HashingEncoder(dim=64).embed_query("休渔期管理"),
        top_k=1,
        texts={"a": "休渔期管理"},
    )
    assert hits[0].chunk.text == "休渔期管理"


def test_save_and_load(tmp_path: Path) -> None:
    chunks = [_chunk("a", "休渔期管理")]
    index = DenseIndex.build(chunks, HashingEncoder(dim=64), "v1")
    path = tmp_path / "index.jsonl"
    info = index.save(path)
    assert info["count"] == 1
    assert len(info["sha256"]) == 64
    loaded = DenseIndex.load(path)
    assert loaded.model_id == "hashing-64"
    assert loaded.index_version == "v1"
    assert loaded.rows[0]["chunk_id"] == "a"


def test_load_rejects_truncated_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonl"
    header = '{"header": {"model_id": "x", "index_version": "v1", "count": 2, "dim": 4}}'
    path.write_text(header + "\n", encoding="utf-8")
    with pytest.raises(DenseError, match="count"):
        DenseIndex.load(path)


def test_index_path_is_model_scoped(tmp_path: Path) -> None:
    path = index_path(tmp_path, "BAAI/bge-small-zh-v1.5", "abc123")
    assert path.name == "BAAI_bge-small-zh-v1.5-abc123.jsonl"
    assert path.parent.name == "embeddings"
