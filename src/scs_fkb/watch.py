from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .config import REPO_ROOT

DEFAULT_WATCH = REPO_ROOT / "configs" / "source-watch.yaml"
DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = "SCS-FKB-watch/1.0 (+https://github.com/HuangXin-erniu/scs-fishery-kb)"
CA_BUNDLE_ENV = "SCS_FKB_CA_BUNDLE"
SYSTEM_CA_BUNDLE = "/etc/ssl/cert.pem"
_ACTIVE_CA_BUNDLE: str | None = None
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


def _ssl_context() -> tuple[ssl.SSLContext, str | None]:
    explicit = os.environ.get(CA_BUNDLE_ENV) or None
    if explicit:
        return ssl.create_default_context(cafile=explicit), explicit
    return ssl.create_default_context(), None


def _fallback_bundle() -> str | None:
    return SYSTEM_CA_BUNDLE if Path(SYSTEM_CA_BUNDLE).is_file() else None


def _is_certificate_error(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(
        exc
    )


def _default_opener(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict, bytes]:
    global _ACTIVE_CA_BUNDLE
    request = urllib.request.Request(url, headers=headers, method="GET")
    context, explicit = _ssl_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:  # noqa: S310
            return response.status, dict(response.headers), response.read()
    except urllib.error.URLError as exc:
        fallback = _fallback_bundle()
        if explicit is None and fallback and _is_certificate_error(exc):
            retry = ssl.create_default_context(cafile=fallback)
            with urllib.request.urlopen(request, timeout=timeout, context=retry) as response:  # noqa: S310
                _ACTIVE_CA_BUNDLE = fallback
                return response.status, dict(response.headers), response.read()
        raise


def check_source(
    entry: dict[str, Any],
    opener: OPENER | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """Fetch one watched page and classify it against its recorded baseline."""
    fetch = opener or _default_opener
    headers = {"User-Agent": user_agent}
    record: dict[str, Any] = {
        "id": str(entry["id"]),
        "ca_bundle": _ACTIVE_CA_BUNDLE,
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
        record["sha256"] = entry.get("sha256")
        return record
    if status >= 400:
        record.update(status="unreachable", error=f"http_{status}")
        return record

    digest = hashlib.sha256(body or b"").hexdigest()
    record["sha256"] = digest
    baseline = entry.get("sha256")
    if not baseline:
        record["status"] = "unbaselined"
    elif baseline == digest:
        record["status"] = "ok"
    else:
        record["status"] = "changed"
    return record


def run_watch(
    config_path: Path | str = DEFAULT_WATCH,
    opener: OPENER | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Check every watched source, or replay the recorded statuses without a socket."""
    data = load_watch(config_path)
    defaults = data.get("defaults") or {}
    timeout = float(defaults.get("timeout_seconds") or DEFAULT_TIMEOUT)
    user_agent = str(defaults.get("user_agent") or DEFAULT_USER_AGENT)

    results: list[dict[str, Any]] = []
    for entry in data["sources"]:
        if offline:
            recorded = str(entry.get("status") or "unchecked")
            results.append(
                {
                    "id": str(entry["id"]),
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
                check_source(entry, opener=opener, timeout=timeout, user_agent=user_agent)
            )

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1
    return {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "offline": offline,
        "results": results,
        "summary": summary,
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
