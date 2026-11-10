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
WEB_MODES = ("off", "auto", "on")
MAX_LEADS = 2


class WebPolicyError(RuntimeError):
    """Raised when the allowlist or policy is malformed."""


@dataclass(frozen=True)
class AllowedSource:
    domain: str
    publisher: str
    tier: str


@dataclass(frozen=True)
class WebConfig:
    allowlist: list[AllowedSource]
    settings: dict[str, Any]

    @property
    def domain_count(self) -> int:
        return len(self.allowlist)


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


def load_web_config(path: Path | str = DEFAULT_WEB_SOURCES) -> WebConfig:
    """Load the allowlist and the provider/limit settings from one file."""
    source_path = Path(path)
    data = yaml.safe_load(source_path.read_text(encoding="utf-8")) if source_path.is_file() else {}
    if not isinstance(data, dict):
        data = {}
    return WebConfig(allowlist=load_allowlist(source_path), settings=provider_settings(data))


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


def normalize_mode(value: str | None) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in WEB_MODES else "off"


def should_search(
    question: str,
    *,
    nature: str = "",
    local_abstained: bool = False,
    explicit: bool = False,
    stale_evidence: bool = False,
) -> tuple[bool, str]:
    """Decide whether an automatic fetch is justified for this question."""
    if explicit:
        return True, "explicit"
    if stale_evidence:
        return True, "stale_evidence"
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
    limits = data.get("limits") if isinstance(data.get("limits"), dict) else {}
    refresh = data.get("refresh") if isinstance(data.get("refresh"), dict) else {}
    return {
        "searxng_url": str(provider.get("searxng_url") or "").strip(),
        "fallback": str(provider.get("fallback") or "ddgs"),
        "max_results": max(1, min(int(provider.get("max_results") or 5), 10)),
        "timeout_seconds": float(
            provider.get("timeout_seconds") or refresh.get("timeout_seconds") or 10
        ),
        "backend": str(provider.get("backend") or "auto"),
        "engines": str(provider.get("engines") or "").strip(),
        "site_hint": str(provider.get("site_hint") or "").strip(),
        "max_evidences": max(1, min(int(limits.get("max_evidences") or MAX_LEADS), MAX_LEADS)),
        "max_bytes": max(1_000_000, min(int(limits.get("max_bytes") or 2_000_000), 4_000_000)),
        "snippet_chars": max(80, min(int(limits.get("snippet_chars") or 300), 500)),
        "spacing_seconds": max(0.0, min(float(limits.get("spacing_seconds") or 2.0), 10.0)),
        "cache_entries": max(20, min(int(limits.get("cache_entries") or 200), 1000)),
        "user_agent": str(refresh.get("user_agent") or "scs-fkb-web/1.0"),
    }


__all__ = [
    "DEFAULT_TTL_DAYS",
    "DEFAULT_WEB_SOURCES",
    "FRESHNESS_WORDS",
    "MAX_LEADS",
    "TTL_DAYS",
    "WEB_MODES",
    "AllowedSource",
    "WebConfig",
    "WebPolicyError",
    "find_allowed",
    "load_allowlist",
    "load_web_config",
    "normalize_mode",
    "provider_settings",
    "should_search",
    "ttl_days",
]
