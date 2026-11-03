from __future__ import annotations

from pathlib import Path

import yaml

from scs_fkb.answer import citation_text, make_citation
from scs_fkb.ingest import web_card_documents
from scs_fkb.models import SearchHit


def _card(card_id: str, status: str = "ok", file: str | None = None) -> dict:
    return {
        "id": card_id,
        "topic": "species",
        "title": "测试物种页",
        "publisher": "WoRMS",
        "url": f"https://www.marinespecies.org/{card_id}.html",
        "fetched_at": "2026-11-03T08:00:00+00:00",
        "sha256": "a" * 64,
        "content_type": "text/html",
        "license": "cc-by",
        "sensitivity": "public",
        "source_class": "reference",
        "file": file or f"{card_id}/text.txt",
        "status": status,
        "excerpt": "测试",
    }


def _write(tmp_path: Path, cards: list[dict]) -> Path:
    path = tmp_path / "web-cards.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "cards": cards}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def _cache(
    tmp_path: Path, card_id: str, text: str = "黄鳍金枪鱼分布于南海。\n\n幼鱼栖息于表层。"
) -> None:
    target = tmp_path / "web" / card_id / "text.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_ok_cards_become_documents_and_chunks(tmp_path: Path) -> None:
    _cache(tmp_path, "WEB-TEST-001")
    cards = _write(tmp_path, [_card("WEB-TEST-001")])
    documents, chunks, entries, counts = web_card_documents(cards, tmp_path, 400)
    assert [doc.doc_id for doc in documents] == ["WEB-TEST-001"]
    assert documents[0].doc_type == "web_card"
    assert chunks and all(chunk.url.endswith("WEB-TEST-001.html") for chunk in chunks)
    assert all(chunk.retrieved_at.startswith("2026-11-03") for chunk in chunks)
    assert entries[0]["kind"] == "web_card"
    assert counts["WEB-TEST-001"] == len(chunks)


def test_failed_and_cache_less_cards_are_skipped(tmp_path: Path) -> None:
    _cache(tmp_path, "WEB-TEST-001")
    cards = _write(
        tmp_path,
        [
            _card("WEB-TEST-001"),
            _card("WEB-TEST-002", status="failed"),
            _card("WEB-TEST-003"),
        ],
    )
    documents, _, _, _ = web_card_documents(cards, tmp_path, 400)
    assert [doc.doc_id for doc in documents] == ["WEB-TEST-001"]


def test_citation_renders_url_and_fetch_date(tmp_path: Path) -> None:
    _cache(tmp_path, "WEB-TEST-001")
    cards = _write(tmp_path, [_card("WEB-TEST-001")])
    _, chunks, _, _ = web_card_documents(cards, tmp_path, 400)
    citation = make_citation(SearchHit(chunk=chunks[0], score=1.0), "黄鳍金枪鱼分布于南海。")
    text = citation_text(citation)
    assert "WEB-TEST-001" in text
    assert "https://www.marinespecies.org/WEB-TEST-001.html" in text
    assert "2026-11-03" in text


def test_missing_cards_file_is_empty(tmp_path: Path) -> None:
    documents, chunks, entries, counts = web_card_documents(tmp_path / "absent.yaml", tmp_path, 400)
    assert documents == [] and chunks == [] and entries == [] and counts == {}
