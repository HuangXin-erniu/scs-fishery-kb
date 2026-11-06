from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_WEB_SOURCES = Path("configs") / "web-sources.yaml"
FRESHNESS_WORDS = (
    "最新",
    "今年",
    "现在",
    "目前",
    "现行",
    "当前",
    "有效期",
    "是否有效",
    "台风",
    "预警",
    "开渔",
    "休渔",
    "禁渔",
    "截至",
)
TTL_DAYS = {
    "warning": 7,
    "status": 7,
    "rule": 30,
    "definition": 90,
    "identification": 90,
    "statistics": 365,
    "history": 365,
}
DEFAULT_TTL_DAYS = 30


class WebPolicyError(RuntimeError):
    """Raised when the allowlist or policy is malformed."""


@dataclass(frozen=True)
class AllowedSource:
    domain: str
    publisher: str
    tier: str


def load_allowlist(path: Path | str = DEFAULT_WEB_SOURCES) -> list[AllowedSource]:
    source_path = Path(path)
    if not source_path.is_file():
        raise WebPolicyError(f"allowlist not found: {source_path}")
    data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    entries = data.get("allowlist") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise WebPolicyError(f"allowlist is empty: {source_path}")
    allowed: list[AllowedSource] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise WebPolicyError(f"allowlist entry is not a mapping: {entry!r}")
        domain = str(entry.get("domain") or "").strip().lower()
        publisher = str(entry.get("publisher") or "").strip()
        tier = str(entry.get("tier") or "").strip().upper()
        if not domain or not publisher or tier not in {"A", "B", "C", "D"}:
            raise WebPolicyError(f"malformed allowlist entry: {entry!r}")
        allowed.append(AllowedSource(domain=domain, publisher=publisher, tier=tier))
    return allowed


def find_allowed(url: str, allowlist: list[AllowedSource]) -> AllowedSource | None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        return None
    host = (parts.hostname or "").lower()
    for entry in allowlist:
        if host == entry.domain or host.endswith("." + entry.domain):
            return entry
    return None


def ttl_days(nature: str) -> int:
    return TTL_DAYS.get(str(nature or ""), DEFAULT_TTL_DAYS)


def should_search(
    question: str,
    *,
    nature: str = "",
    local_abstained: bool = False,
    explicit: bool = False,
) -> tuple[bool, str]:
    if explicit:
        return True, "explicit"
    if nature in {"status", "warning"}:
        return True, f"nature={nature}"
    if any(word in question for word in FRESHNESS_WORDS):
        return True, "freshness_cue"
    if local_abstained:
        return True, "canonical_abstained"
    return False, "not_needed"


def provider_settings(data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    provider = data.get("provider") if isinstance(data.get("provider"), dict) else {}
    return {
        "searxng_url": str(provider.get("searxng_url") or "").strip(),
        "fallback": str(provider.get("fallback") or "ddgs"),
        "max_results": int(provider.get("max_results") or 5),
        "timeout_seconds": float(provider.get("timeout_seconds") or 15),
        "backend": str(provider.get("backend") or "auto"),
    }


__all__ = [
    "DEFAULT_TTL_DAYS",
    "DEFAULT_WEB_SOURCES",
    "FRESHNESS_WORDS",
    "TTL_DAYS",
    "AllowedSource",
    "WebPolicyError",
    "find_allowed",
    "load_allowlist",
    "provider_settings",
    "should_search",
    "ttl_days",
]
