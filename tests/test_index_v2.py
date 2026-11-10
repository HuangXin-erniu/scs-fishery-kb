from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

pytest.importorskip("lancedb")
pytest.importorskip("llama_index")

from scs_fkb.embed import HashingEncoder
from scs_fkb.index_v2 import (
    build_index_v2,
    current_version,
    dense_search,
    list_versions,
    load_chunks_v2,
    open_index,
    prune_versions,
    rollback_index,
)
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


def test_changed_document_builds_a_new_immutable_version(tmp_path: Path) -> None:
    root = tmp_path / "data"
    _write(
        root,
        [
            _chunk("a", "POL-T-001", "南海区休渔时间。"),
            _chunk("b", "POL-T-002", "捕捞许可证申请。"),
        ],
    )
    encoder = HashingEncoder(64)
    first = build_index_v2(root, encoder)
    _write(
        root,
        [
            _chunk("a", "POL-T-001", "南海区休渔时间（更新）。"),
            _chunk("b", "POL-T-002", "捕捞许可证申请。"),
        ],
    )
    result = build_index_v2(root, encoder)
    assert result.index_version != first.index_version
    assert result.version_path and Path(result.version_path).is_dir()
    assert result.rebuilt == ["POL-T-001", "POL-T-002"]
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


def _version(root: Path, name: str, built_at: str) -> None:
    directory = root / "v2" / "index" / "versions" / name
    (directory / "lancedb").mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "index_version": name,
                "built_at": built_at,
                "documents": 1,
                "chunks": 1,
            }
        ),
        encoding="utf-8",
    )


def _pointer(root: Path, name: str) -> None:
    path = root / "v2" / "index" / "current.json"
    path.write_text(json.dumps({"index_version": name}), encoding="utf-8")


def test_list_current_rollback_and_prune(tmp_path: Path) -> None:
    _version(tmp_path, "aaa", "2026-11-01T00:00:00+00:00")
    _version(tmp_path, "bbb", "2026-11-02T00:00:00+00:00")
    _version(tmp_path, "ccc", "2026-11-03T00:00:00+00:00")
    _pointer(tmp_path, "ccc")

    assert current_version(tmp_path)["index_version"] == "ccc"
    assert [row["index_version"] for row in list_versions(tmp_path)] == ["ccc", "bbb", "aaa"]

    rolled = rollback_index(tmp_path)
    assert rolled["rolled_back_from"] == "ccc"
    assert rolled["rolled_back_to"] == "bbb"
    assert current_version(tmp_path)["index_version"] == "bbb"

    removed = prune_versions(tmp_path, keep=2)
    assert removed == ["aaa"]
    assert not (tmp_path / "v2" / "index" / "versions" / "aaa").exists()


def test_rollback_needs_a_previous_version(tmp_path: Path) -> None:
    _version(tmp_path, "only", "2026-11-01T00:00:00+00:00")
    _pointer(tmp_path, "only")
    try:
        rollback_index(tmp_path)
    except Exception as exc:  # noqa: BLE001 - the message is the contract
        assert "previous" in str(exc)
    else:  # pragma: no cover - must raise
        raise AssertionError("rollback succeeded with a single version")


def test_prune_keep_must_be_positive(tmp_path: Path) -> None:
    try:
        prune_versions(tmp_path, keep=0)
    except Exception as exc:  # noqa: BLE001
        assert "keep" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("prune accepted keep=0")
