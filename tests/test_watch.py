from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.watch import (
    check_source,
    load_baseline,
    run_watch,
    save_baseline,
    write_report,
)

BODY = b"<html><body>2026 marine seasonal closure notice</body></html>"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _config(tmp_path: Path, *, sha: str | None = DIGEST) -> Path:
    entry = {
        "id": "WATCH-MOA-TEST",
        "url": "https://www.moa.gov.cn/test",
        "authority": "A",
        "publisher": "农业农村部",
        "cadence": "monthly",
        "note": "test entry",
        "status": "ok",
    }
    if sha is not None:
        entry["sha256"] = sha
    path = tmp_path / "source-watch.yaml"
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "updated_at": "2026-11-10", "sources": [entry]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path


def _opener(url: str, headers: dict[str, str], timeout: float):
    return 200, {"Content-Type": "text/html"}, BODY


def test_check_source_ok_changed_unbaselined_and_unreachable() -> None:
    entry = {"id": "W", "url": "https://www.moa.gov.cn/test", "authority": "A", "publisher": "P"}
    ok = check_source({**entry, "sha256": DIGEST}, opener=_opener)
    assert ok["status"] == "ok"
    assert ok["sha256"] == DIGEST

    changed = check_source({**entry, "sha256": "0" * 64}, opener=_opener)
    assert changed["status"] == "changed"

    unbaselined = check_source(entry, opener=_opener)
    assert unbaselined["status"] == "unbaselined"

    def broken(url, headers, timeout):
        raise OSError("offline")

    unreachable = check_source(entry, opener=broken)
    assert unreachable["status"] == "unreachable"
    assert unreachable["error"] == "OSError"


def test_check_source_uses_local_baseline_and_304() -> None:
    entry = {"id": "W", "url": "https://www.moa.gov.cn/test", "authority": "A", "publisher": "P"}
    assert check_source(entry, opener=_opener, baseline=DIGEST)["status"] == "ok"

    def not_modified(url, headers, timeout):
        return 304, {}, b""

    assert check_source(entry, opener=not_modified, baseline=DIGEST)["status"] == "ok"


def test_run_watch_offline_replays_without_calling_the_opener(tmp_path: Path) -> None:
    path = _config(tmp_path)
    calls: list[str] = []

    def opener(url, headers, timeout):
        calls.append(url)
        return 200, {}, BODY

    report = run_watch(path, opener=opener, offline=True)
    assert report["offline"] is True
    assert report["summary"] == {"ok": 1}
    assert calls == []


def test_run_watch_live_and_baseline_round_trip(tmp_path: Path) -> None:
    path = _config(tmp_path, sha=None)
    report = run_watch(path, opener=_opener)
    assert report["summary"] == {"unbaselined": 1}

    baseline = tmp_path / "watch" / "baseline.json"
    assert save_baseline(report, baseline) == 1
    assert load_baseline(baseline)["WATCH-MOA-TEST"] == DIGEST

    again = run_watch(path, opener=_opener, baseline_path=baseline)
    assert again["summary"] == {"ok": 1}


def test_write_report_creates_the_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "watch.json"
    write_report({"schema_version": 1, "results": []}, target)
    assert target.is_file()


def test_load_baseline_ignores_missing_or_broken_files(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "missing.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_baseline(broken) == {}
    assert date.today().isoformat()
