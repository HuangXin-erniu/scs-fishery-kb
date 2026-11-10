from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .evidence import (
    WebEvidence,
    citation,
    evidence_id,
    get_fresh,
    save_evidence,
)
from .fetch import FetchedPage, FetchError, fetch_page
from .policy import AllowedSource, find_allowed, normalize_mode, should_search, ttl_days
from .providers import ProviderError, SearchProvider

MIN_TEXT_CHARS = 60


@dataclass
class WebSearchResult:
    triggered: bool
    reason: str
    query: str
    provider: str
    mode: str = "auto"
    evidences: list[WebEvidence] = field(default_factory=list)
    dropped: list[dict[str, str]] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    cached: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered": self.triggered,
            "reason": self.reason,
            "query": self.query,
            "provider": self.provider,
            "mode": self.mode,
            "evidences": [item.to_dict() for item in self.evidences],
            "citations": [citation(item) for item in self.evidences],
            "dropped": self.dropped,
            "failures": self.failures,
            "cached": self.cached,
        }


Fetcher = Callable[[str, list[AllowedSource]], FetchedPage]


def _domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def search_web(
    question: str,
    *,
    nature: str,
    allowlist: list[AllowedSource],
    provider: SearchProvider,
    data_root: Path | str,
    mode: str = "auto",
    explicit: bool = False,
    local_abstained: bool = False,
    stale_evidence: bool = False,
    max_results: int = 5,
    max_evidences: int = 2,
    site_hint: str = "",
    spacing_seconds: float = 2.0,
    max_bytes: int = 2_000_000,
    snippet_chars: int = 300,
    cache_entries: int = 200,
    user_agent: str = "scs-fkb-web/1.0",
    fetcher: Fetcher | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    now: datetime | None = None,
) -> WebSearchResult:
    """Search, filter, fetch and cache web evidence for one question.

    ``mode=off`` never touches the provider. ``mode=on`` is an explicit request.
    ``auto`` follows :func:`should_search`. Fetching is sequential with a spacing
    delay so a single question cannot burst a publisher's site.
    """
    mode = normalize_mode(mode)
    provider_name = str(getattr(provider, "name", "unknown"))
    if mode == "off":
        return WebSearchResult(
            triggered=False,
            reason="mode_off",
            query=question,
            provider=provider_name,
            mode=mode,
        )
    triggered, reason = should_search(
        question,
        nature=nature,
        local_abstained=local_abstained,
        explicit=explicit or mode == "on",
        stale_evidence=stale_evidence,
    )
    if not triggered:
        return WebSearchResult(
            triggered=False,
            reason=reason,
            query=question,
            provider=provider_name,
            mode=mode,
        )

    def _search(query: str) -> list[Any]:
        return provider.search(query, max_results=max(max_results * 3, max_results))

    def _filter(results: list[Any]) -> tuple[list[tuple[Any, AllowedSource]], list[dict[str, str]]]:
        kept: list[tuple[Any, AllowedSource]] = []
        discarded: list[dict[str, str]] = []
        seen: set[str] = set()
        for result in results:
            if result.url in seen:
                continue
            seen.add(result.url)
            allowed = find_allowed(result.url, allowlist)
            if allowed is None:
                discarded.append({"url": result.url, "reason": "not_allowlisted_or_not_https"})
                continue
            kept.append((result, allowed))
            if len(kept) >= max_results:
                break
        return kept, discarded

    try:
        accepted, dropped = _filter(_search(question))
        if not accepted and site_hint and site_hint not in question:
            try:
                retry, retry_dropped = _filter(_search(f"{question} site:{site_hint}"))
            except ProviderError:
                retry, retry_dropped = [], []
            accepted.extend(retry)
            dropped.extend(retry_dropped)
    except ProviderError as exc:
        return WebSearchResult(
            triggered=True,
            reason=reason,
            query=question,
            provider=provider_name,
            mode=mode,
            failures=[{"stage": "search", "error": str(exc)}],
        )

    current = now or datetime.now(UTC)
    evidences: list[WebEvidence] = []
    failures: list[dict[str, str]] = []
    cached = 0
    fetched = 0
    if fetcher is None:

        def page_fetcher(url: str, allowed: list[AllowedSource]) -> FetchedPage:
            return fetch_page(
                url,
                allowed,
                max_bytes=max_bytes,
                user_agent=user_agent,
            )

    else:
        page_fetcher = fetcher

    for result, allowed in accepted:
        if len(evidences) >= max_evidences:
            break
        fresh = get_fresh(data_root, result.url, now=current)
        if fresh is not None:
            evidences.append(fresh)
            cached += 1
            continue
        if fetched and spacing_seconds > 0:
            sleeper(spacing_seconds)
        fetched += 1
        try:
            page = page_fetcher(result.url, allowlist)
        except FetchError as exc:
            failures.append({"url": result.url, "error": str(exc)})
            continue
        if len(page.text.strip()) < MIN_TEXT_CHARS:
            failures.append({"url": result.url, "error": "web.empty_text"})
            continue
        identifier = evidence_id(page.final_url, page.content_hash)
        evidence = WebEvidence(
            evidence_id=identifier,
            url=result.url,
            canonical_url=page.final_url,
            title=result.title or page.title,
            publisher=allowed.publisher,
            domain=_domain(page.final_url),
            authority_tier=allowed.tier,
            source_class="reference",
            fetched_at=current.replace(microsecond=0).isoformat(),
            content_hash=page.content_hash,
            snippet=" ".join((result.snippet or page.text[:snippet_chars]).split())[:snippet_chars],
            text_path="",
            search_query=question,
            rank=result.rank,
            ttl_days=ttl_days(nature),
            status="fetched",
        )
        evidences.append(save_evidence(data_root, evidence, page.text, cache_entries=cache_entries))

    return WebSearchResult(
        triggered=True,
        reason=reason,
        query=question,
        provider=provider_name,
        mode=mode,
        evidences=evidences,
        dropped=dropped,
        failures=failures,
        cached=cached,
    )


__all__ = ["Fetcher", "WebSearchResult", "search_web"]
