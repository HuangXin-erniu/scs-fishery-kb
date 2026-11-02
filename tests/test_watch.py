from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from scs_fkb.watch import WatchError, check_source, load_watch, run_watch

BODY = b"page body"


def _entry(**overrides):
    entry = {
        "id": "WATCH-TEST",
        "url": "https://example.invalid/page",
        "authority": "A",
        "publisher": "test publisher",
        "status": "unchecked",
    }
    entry.update(overrides)
    return entry


def _config(tmp_path: Path, sources: list[dict]) -> Path:
    path = tmp_path / "watch.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "sources": sources}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def _opener(status: int, body: bytes = BODY, headers: dict | None = None):
    def fetch(url: str, request_headers: dict, timeout: float):
        return status, headers or {}, body

    return fetch


def test_matching_baseline_is_ok() -> None:
    digest = hashlib.sha256(BODY).hexdigest()
    record = check_source(_entry(sha256=digest), opener=_opener(200))
    assert record["status"] == "ok"
    assert record["sha256"] == digest


def test_different_body_is_changed() -> None:
    record = check_source(_entry(sha256="0" * 64), opener=_opener(200))
    assert record["status"] == "changed"


def test_missing_baseline_is_unbaselined() -> None:
    record = check_source(_entry(), opener=_opener(200))
    assert record["status"] == "unbaselined"


def test_not_modified_counts_as_ok() -> None:
    record = check_source(_entry(sha256="0" * 64), opener=_opener(304))
    assert record["status"] == "ok"
    assert record["sha256"] == "0" * 64


def test_http_error_is_unreachable() -> None:
    record = check_source(_entry(), opener=_opener(404))
    assert record["status"] == "unreachable"
    assert record["http_status"] == 404


def test_timeout_is_unreachable() -> None:
    def fetch(url: str, request_headers: dict, timeout: float):
        raise TimeoutError("slow")

    record = check_source(_entry(), opener=fetch)
    assert record["status"] == "unreachable"
    assert record["error"] == "TimeoutError"


def test_offline_never_calls_the_opener(tmp_path: Path) -> None:
    path = _config(tmp_path, [_entry(status="ok", sha256="a" * 64)])

    def fetch(url: str, request_headers: dict, timeout: float):
        raise AssertionError("offline mode must not open a socket")

    report = run_watch(path, opener=fetch, offline=True)
    assert report["offline"] is True
    assert report["results"][0]["status"] == "ok"
    assert report["summary"] == {"ok": 1}


def test_malformed_entry_is_rejected(tmp_path: Path) -> None:
    path = _config(tmp_path, [{"id": "X", "authority": "A", "publisher": "p"}])
    with pytest.raises(WatchError, match="incomplete"):
        load_watch(path)


def test_unknown_authority_is_rejected(tmp_path: Path) -> None:
    path = _config(tmp_path, [_entry(authority="Z")])
    with pytest.raises(WatchError, match="authority"):
        load_watch(path)
