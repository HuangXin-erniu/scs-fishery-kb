from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .evidence import WebEvidence, citation, evidence_id, get_fresh, save_evidence
from .fetch import FetchedPage, FetchError, fetch_page
from .policy import AllowedSource, find_allowed, should_search, ttl_days
from .providers import ProviderError, SearchProvider


@dataclass
class WebSearchResult:
    triggered: bool
    reason: str
    query: str
    provider: str
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
            "evidences": [item.to_dict() for item in self.evidences],
            "citations": [citation(item) for item in self.evidences],
            "dropped": self.dropped,
            "failures": self.failures,
            "cached": self.cached,
        }


Fetcher = Callable[[str, list[AllowedSource]], FetchedPage]


def _default_fetcher(url: str, allowlist: list[AllowedSource]) -> FetchedPage:
    return fetch_page(url, allowlist)


def _domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def search_web(
    question: str,
    *,
    nature: str,
    allowlist: list[AllowedSource],
    provider: SearchProvider,
    data_root: Path | str,
    max_results: int = 5,
    explicit: bool = False,
    local_abstained: bool = False,
    fetcher: Fetcher | None = None,
    now: datetime | None = None,
) -> WebSearchResult:
    triggered, reason = should_search(
        question,
        nature=nature,
        local_abstained=local_abstained,
        explicit=explicit,
    )
    if not triggered:
        return WebSearchResult(
            triggered=False,
            reason=reason,
            query=question,
            provider=str(getattr(provider, "name", "unknown")),
        )
    try:
        results = provider.search(question, max_results=max(max_results * 3, max_results))
    except ProviderError as exc:
        return WebSearchResult(
            triggered=True,
            reason=reason,
            query=question,
            provider=str(getattr(provider, "name", "unknown")),
            failures=[{"stage": "search", "error": str(exc)}],
        )

    accepted: list[tuple[Any, AllowedSource]] = []
    dropped: list[dict[str, str]] = []
    for result in results:
        allowed = find_allowed(result.url, allowlist)
        if allowed is None:
            dropped.append({"url": result.url, "reason": "not_allowlisted_or_not_https"})
            continue
        accepted.append((result, allowed))
        if len(accepted) >= max_results:
            break

    current = now or datetime.now(UTC)
    evidences: list[WebEvidence] = []
    failures: list[dict[str, str]] = []
    cached = 0
    page_fetcher = fetcher or _default_fetcher
    for result, allowed in accepted:
        fresh = get_fresh(data_root, result.url, now=current)
        if fresh is not None:
            evidences.append(fresh)
            cached += 1
            continue
        try:
            page = page_fetcher(result.url, allowlist)
        except FetchError as exc:
            failures.append({"url": result.url, "error": str(exc)})
            continue
        if not page.text.strip():
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
            snippet=" ".join((result.snippet or page.text[:200]).split())[:300],
            text_path="",
            search_query=question,
            rank=result.rank,
            ttl_days=ttl_days(nature),
            status="fetched",
        )
        evidences.append(save_evidence(data_root, evidence, page.text))

    return WebSearchResult(
        triggered=True,
        reason=reason,
        query=question,
        provider=str(getattr(provider, "name", "unknown")),
        evidences=evidences,
        dropped=dropped,
        failures=failures,
        cached=cached,
    )


__all__ = ["Fetcher", "WebSearchResult", "search_web"]
