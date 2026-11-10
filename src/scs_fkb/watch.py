"""Read-only watch list: fetch authoritative index pages and compare content hashes.

The checker never downloads a document into the register, never edits
``configs/corpus.yaml`` and never promotes a candidate. A changed page becomes a
report row (and, when asked, a candidate draft under the run root) for a human to
review.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import REPO_ROOT
from .registry import load_registry
from .web_v2.net import CA_ENV, open_url

DEFAULT_WATCH = REPO_ROOT / "configs" / "source-watch.yaml"
DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = "SCS-FKB-watch/1.0 (+https://github.com/HuangXin-erniu/scs-fishery-kb)"
STATUSES = {"ok", "changed", "unbaselined", "unreachable"}
TIERS = {"A", "B", "C"}
OPENER = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]


class WatchError(RuntimeError):
    """Raised when the watch list is missing or malformed."""


def load_watch(path: Path | str = DEFAULT_WATCH) -> dict[str, Any]:
    watch_path = Path(path)
    if not watch_path.is_file():
        raise WatchError(f"watch list not found: {watch_path}")
    data = yaml.safe_load(watch_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise WatchError(f"unsupported watch schema: {watch_path}")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise WatchError(f"watch list has no sources: {watch_path}")
    seen: set[str] = set()
    for entry in sources:
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("url"):
            raise WatchError(f"watch entry is incomplete: {entry}")
        if entry["id"] in seen:
            raise WatchError(f"duplicate watch id: {entry['id']}")
        seen.add(str(entry["id"]))
        if entry.get("authority") not in TIERS:
            raise WatchError(f"watch entry has no authority tier: {entry['id']}")
        if not entry.get("publisher"):
            raise WatchError(f"watch entry has no publisher: {entry['id']}")
        if entry.get("status") is not None and entry["status"] not in STATUSES | {"unchecked"}:
            raise WatchError(f"watch entry has an unknown status: {entry['id']}")
    return data


def load_baseline(path: Path | str | None) -> dict[str, str]:
    if not path:
        return {}
    baseline_path = Path(path)
    if not baseline_path.is_file():
        return {}
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = data.get("hashes") if isinstance(data, dict) else None
    if not isinstance(rows, dict):
        return {}
    return {str(key): str(value) for key, value in rows.items() if value}


def save_baseline(report: dict[str, Any], path: Path | str) -> int:
    """Record the hashes observed by a live run; returns how many were written."""
    hashes: dict[str, str] = {}
    for result in report.get("results") or []:
        if not isinstance(result, dict):
            continue
        digest = result.get("sha256")
        if digest and result.get("status") in {"ok", "changed", "unbaselined"}:
            hashes[str(result["id"])] = str(digest)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "checked_at": report.get("checked_at"),
                "hashes": dict(sorted(hashes.items())),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)
    return len(hashes)


def _default_opener(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with open_url(request, timeout) as response:
        return response.status, dict(response.headers), response.read()


def check_source(
    entry: dict[str, Any],
    *,
    opener: OPENER | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    baseline: str | None = None,
) -> dict[str, Any]:
    """Fetch one watched page and classify it against its recorded baseline."""
    fetch = opener or _default_opener
    headers = {"User-Agent": user_agent}
    record: dict[str, Any] = {
        "id": str(entry["id"]),
        "title": str(entry.get("title") or f"{entry.get('publisher', '')} {entry['id']}".strip()),
        "publisher": entry.get("publisher"),
        "ca_bundle": os.environ.get(CA_ENV) or None,
        "url": str(entry["url"]),
        "authority": entry.get("authority"),
        "sha256": None,
        "etag": None,
        "last_modified": None,
        "http_status": None,
        "error": None,
    }
    try:
        status, response_headers, body = fetch(str(entry["url"]), headers, timeout)
    except Exception as exc:  # noqa: BLE001 - network errors are recorded, not raised
        record.update(status="unreachable", error=type(exc).__name__)
        return record

    record["http_status"] = status
    record["etag"] = response_headers.get("ETag") or response_headers.get("etag")
    record["last_modified"] = response_headers.get("Last-Modified") or response_headers.get(
        "last-modified"
    )
    if status == 304:
        record["status"] = "ok"
        record["sha256"] = baseline or entry.get("sha256")
        return record
    if status >= 400:
        record.update(status="unreachable", error=f"http_{status}")
        return record

    digest = hashlib.sha256(body or b"").hexdigest()
    record["sha256"] = digest
    expected = baseline or entry.get("sha256")
    if not expected:
        record["status"] = "unbaselined"
    elif expected == digest:
        record["status"] = "ok"
    else:
        record["status"] = "changed"
    return record


def run_watch(
    config_path: Path | str = DEFAULT_WATCH,
    *,
    opener: OPENER | None = None,
    offline: bool = False,
    baseline_path: Path | str | None = None,
) -> dict[str, Any]:
    """Check every watched source, or replay the recorded statuses without a socket."""
    data = load_watch(config_path)
    defaults = data.get("defaults") or {}
    timeout = float(defaults.get("timeout_seconds") or DEFAULT_TIMEOUT)
    user_agent = str(defaults.get("user_agent") or DEFAULT_USER_AGENT)
    baseline = load_baseline(baseline_path)

    results: list[dict[str, Any]] = []
    for entry in data["sources"]:
        if offline:
            recorded = str(entry.get("status") or "unchecked")
            results.append(
                {
                    "id": str(entry["id"]),
                    "title": str(
                        entry.get("title") or f"{entry.get('publisher', '')} {entry['id']}".strip()
                    ),
                    "publisher": entry.get("publisher"),
                    "url": str(entry["url"]),
                    "authority": entry.get("authority"),
                    "status": recorded if recorded in STATUSES else "unbaselined",
                    "http_status": None,
                    "sha256": entry.get("sha256"),
                    "etag": entry.get("etag"),
                    "last_modified": entry.get("last_modified"),
                    "error": None,
                    "offline": True,
                }
            )
        else:
            results.append(
                check_source(
                    entry,
                    opener=opener,
                    timeout=timeout,
                    user_agent=user_agent,
                    baseline=baseline.get(str(entry["id"])),
                )
            )

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1
    return {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "offline": offline,
        "baseline": str(baseline_path) if baseline_path else None,
        "results": results,
        "summary": summary,
    }


def write_report(report: dict[str, Any], path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def due_report(
    registry_path: Path | str,
    *,
    today: date | None = None,
) -> dict[str, list[dict[str, str]]]:
    """List corpus entries whose review date has arrived."""
    current = today or date.today()
    registry = load_registry(registry_path)
    corpus: list[dict[str, str]] = []
    for source_id, entry in registry.items():
        due = (entry.get("currency") or {}).get("review_due")
        if not due:
            continue
        try:
            when = date.fromisoformat(str(due))
        except ValueError:
            continue
        if when <= current:
            corpus.append({"id": source_id, "review_due": when.isoformat()})
    return {"corpus": sorted(corpus, key=lambda row: row["id"])}


__all__ = [
    "DEFAULT_USER_AGENT",
    "DEFAULT_WATCH",
    "STATUSES",
    "WatchError",
    "check_source",
    "due_report",
    "load_baseline",
    "load_watch",
    "run_watch",
    "save_baseline",
    "write_report",
]
