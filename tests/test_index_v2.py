from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

pytest.importorskip("lancedb")
pytest.importorskip("llama_index")

from scs_fkb.embed import HashingEncoder
from scs_fkb.index_v2 import build_index_v2, dense_search, load_chunks_v2, open_index
from scs_fkb.models import Chunk


def _chunk(chunk_id: str, doc_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_id=doc_id,
        page=1,
        section="第一条",
        text=text,
        token_count=len(text),
        char_start=0,
        char_end=len(text),
        sensitivity="public",
        authority_tier="A",
        level="national",
        source_class="normative",
        jurisdiction="national",
        chunk_type="text",
        parent_id=f"{doc_id}-parent",
    )


def _write(root: Path, chunks: list[Chunk]) -> None:
    path = root / "v2" / "processed" / "chunks.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(asdict(chunk), ensure_ascii=False) for chunk in chunks) + "\n",
        encoding="utf-8",
    )


def test_build_index_is_idempotent_and_queries(tmp_path: Path) -> None:
    root = tmp_path / "data"
    chunks = [
        _chunk("a", "POL-T-001", "南海区休渔时间为五月一日至八月十六日。"),
        _chunk("b", "POL-T-002", "捕捞许可证申请需要提交申请书。"),
    ]
    _write(root, chunks)
    encoder = HashingEncoder(64)
    first = build_index_v2(root, encoder)
    assert first.chunks == 2
    assert first.documents == 2
    assert first.table_rows == 2
    assert first.rebuilt == ["POL-T-001", "POL-T-002"]
    assert (root / "v2/index/manifest.json").is_file()

    second = build_index_v2(root, encoder)
    assert second.no_op is True
    assert second.rebuilt == []

    index = open_index(root, encoder)
    assert dense_search(index, "休渔", top_k=2)


def test_incremental_change_deletes_and_adds_only_that_document(tmp_path: Path) -> None:
    root = tmp_path / "data"
    _write(
        root,
        [
            _chunk("a", "POL-T-001", "南海区休渔时间。"),
            _chunk("b", "POL-T-002", "捕捞许可证申请。"),
        ],
    )
    encoder = HashingEncoder(64)
    build_index_v2(root, encoder)
    _write(
        root,
        [
            _chunk("a", "POL-T-001", "南海区休渔时间（更新）。"),
            _chunk("b", "POL-T-002", "捕捞许可证申请。"),
        ],
    )
    result = build_index_v2(root, encoder)
    assert result.rebuilt == ["POL-T-001"]
    assert result.table_rows == 2


def test_removed_document_is_deleted(tmp_path: Path) -> None:
    root = tmp_path / "data"
    _write(root, [_chunk("a", "POL-T-001", "文本一。"), _chunk("b", "POL-T-002", "文本二。")])
    encoder = HashingEncoder(64)
    build_index_v2(root, encoder)
    _write(root, [_chunk("a", "POL-T-001", "文本一。")])
    result = build_index_v2(root, encoder)
    assert result.removed == ["POL-T-002"]
    assert result.table_rows == 1
    assert [chunk.doc_id for chunk in load_chunks_v2(root)] == ["POL-T-001"]
