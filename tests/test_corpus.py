from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scs_fkb.corpus import CorpusError, _source_from_mapping, resolve_source_file


def _source(location: str, digest: str):
    return _source_from_mapping(
        {
            "id": "DOC-TEST",
            "title": "test",
            "title_zh": "test",
            "publisher": "publisher",
            "type": "notice",
            "format": "html",
            "location": location,
            "license": "public",
            "sensitivity": "public",
            "status": "acquired",
            "hash": digest,
        }
    )


def test_resolve_source_file_accepts_a_single_file_directory(tmp_path: Path) -> None:
    directory = tmp_path / "raw" / "DOC-TEST"
    directory.mkdir(parents=True)
    page = directory / "page.html"
    page.write_bytes(b"page body")
    path, digest = resolve_source_file(
        _source("raw/DOC-TEST", hashlib.sha256(b"page body").hexdigest()), tmp_path
    )
    assert path == page
    assert digest == hashlib.sha256(b"page body").hexdigest()


def test_resolve_source_file_rejects_an_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "raw" / "DOC-TEST").mkdir(parents=True)
    with pytest.raises(CorpusError, match="expected exactly one file"):
        resolve_source_file(_source("raw/DOC-TEST", "0" * 64), tmp_path)


def test_resolve_source_file_rejects_a_multi_file_directory(tmp_path: Path) -> None:
    directory = tmp_path / "raw" / "DOC-TEST"
    directory.mkdir(parents=True)
    (directory / "a.html").write_text("a", encoding="utf-8")
    (directory / "b.html").write_text("b", encoding="utf-8")
    with pytest.raises(CorpusError, match="expected exactly one file"):
        resolve_source_file(_source("raw/DOC-TEST", "0" * 64), tmp_path)
