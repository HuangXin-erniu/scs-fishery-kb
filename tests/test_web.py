from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from scs_fkb.web import WebError, is_allowed, load_cards, load_web_sources, refresh

SOURCES = {
    "schema_version": 1,
    "allowlist": [
        {"domain": "moa.gov.cn", "publisher": "农业农村部", "tier": "A"},
        {"domain": "noaa.gov", "publisher": "NOAA", "tier": "A"},
    ],
    "topics": {"species": {"cadence_days": 30, "max_cards": 4}},
    "refresh": {
        "timeout_seconds": 1,
        "rate_limit_seconds": 0,
        "max_bytes": 10000,
        "user_agent": "test",
    },
}

CARD = {
    "id": "WEB-TEST-001",
    "topic": "species",
    "title": "测试页面",
    "publisher": "农业农村部",
    "url": "https://www.moa.gov.cn/test.html",
    "fetched_at": "",
    "sha256": "",
    "content_type": "text/html",
    "license": "public",
    "sensitivity": "public",
    "source_class": "reference",
    "file": "",
    "status": "ok",
    "excerpt": "",
}


def _write(tmp_path: Path, cards: list[dict]) -> tuple[Path, Path]:
    sources_path = tmp_path / "web-sources.yaml"
    sources_path.write_text(yaml.safe_dump(SOURCES, allow_unicode=True), encoding="utf-8")
    cards_path = tmp_path / "web-cards.yaml"
    cards_path.write_text(
        yaml.safe_dump({"schema_version": 1, "cards": cards}, allow_unicode=True),
        encoding="utf-8",
    )
    return cards_path, sources_path


def test_allowlist_accepts_subdomains_and_rejects_http() -> None:
    allowlist = SOURCES["allowlist"]
    assert is_allowed("https://www.moa.gov.cn/x", allowlist)[0] is True
    assert is_allowed("https://coastwatch.noaa.gov/x", allowlist)[0] is True
    assert is_allowed("http://www.moa.gov.cn/x", allowlist)[0] is False
    assert is_allowed("https://evil.example/x", allowlist)[0] is False


def test_refresh_writes_private_text_and_public_metadata(tmp_path: Path) -> None:
    cards_path, sources_path = _write(tmp_path, [dict(CARD)])
    cache = tmp_path / "cache"

    def fetcher(url: str) -> tuple[bytes, str]:
        return "<html><body><p>渔业测试文本内容。</p></body></html>".encode(), "text/html"

    now = datetime(2026, 11, 3, tzinfo=UTC)
    report = refresh(cards_path, sources_path, cache, fetcher=fetcher, now=now)
    assert report["ok"] == 1 and report["failed"] == 0
    card = load_cards(cards_path)["cards"][0]
    assert card["status"] == "ok"
    assert len(card["sha256"]) == 64
    assert card["fetched_at"].startswith("2026-11-03")
    assert (cache / "WEB-TEST-001" / "text.txt").read_text(encoding="utf-8").strip()
    assert card["excerpt"]


def test_refresh_records_failure_without_aborting(tmp_path: Path) -> None:
    second = dict(CARD, id="WEB-TEST-002", url="https://www.moa.gov.cn/fail.html")
    cards_path, sources_path = _write(tmp_path, [dict(CARD), second])
    cache = tmp_path / "cache"

    def fetcher(url: str) -> tuple[bytes, str]:
        if "fail" in url:
            raise OSError("boom")
        return "<html><body><p>正常文本。</p></body></html>".encode(), "text/html"

    report = refresh(cards_path, sources_path, cache, fetcher=fetcher)
    assert report["ok"] == 1 and report["failed"] == 1
    cards = {card["id"]: card for card in load_cards(cards_path)["cards"]}
    assert cards["WEB-TEST-001"]["status"] == "ok"
    assert cards["WEB-TEST-002"]["status"] == "failed"
    assert "boom" in cards["WEB-TEST-002"]["error"]


def test_refresh_blocks_a_non_allowlisted_host(tmp_path: Path) -> None:
    card = dict(CARD, url="https://evil.example/x.html")
    cards_path, sources_path = _write(tmp_path, [card])
    called: list[str] = []

    def fetcher(url: str) -> tuple[bytes, str]:
        called.append(url)
        return b"<html><body><p>x</p></body></html>", "text/html"

    report = refresh(cards_path, sources_path, tmp_path / "cache", fetcher=fetcher)
    assert report["failed"] == 1
    assert called == []
    assert "not allowlisted" in load_cards(cards_path)["cards"][0]["error"]


def test_malformed_card_is_rejected(tmp_path: Path) -> None:
    cards_path, sources_path = _write(tmp_path, [dict(CARD, id="BAD")])
    with pytest.raises(WebError, match="bad id"):
        load_cards(cards_path)
    with pytest.raises(WebError, match="bad id"):
        refresh(cards_path, sources_path, tmp_path / "cache", fetcher=lambda url: (b"", ""))


def test_sources_config_requires_allowlist(tmp_path: Path) -> None:
    path = tmp_path / "web-sources.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "allowlist": []}), encoding="utf-8")
    with pytest.raises(WebError, match="allowlist"):
        load_web_sources(path)


def test_refresh_extracts_json(tmp_path: Path) -> None:
    card = dict(CARD, url="https://www.noaa.gov/rest/x")
    cards_path, sources_path = _write(tmp_path, [card])

    def fetcher(url: str) -> tuple[bytes, str]:
        return b'{"scientificname": "Larimichthys crocea"}', "application/json"

    report = refresh(cards_path, sources_path, tmp_path / "cache", fetcher=fetcher)
    assert report["ok"] == 1
    text = (tmp_path / "cache" / "WEB-TEST-001" / "text.txt").read_text(encoding="utf-8")
    assert "Larimichthys crocea" in text
