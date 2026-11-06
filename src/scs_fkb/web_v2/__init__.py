"""Ephemeral web evidence: allowlist, providers, fetch, cache and TTL."""

from .evidence import (
    LABEL,
    WebEvidence,
    citation,
    get_fresh,
    is_fresh,
    promotion_draft,
)
from .fetch import FetchedPage, FetchError, fetch_page
from .policy import (
    AllowedSource,
    find_allowed,
    load_allowlist,
    should_search,
    ttl_days,
)
from .providers import (
    DuckDuckGoProvider,
    ProviderError,
    SearchResult,
    SearXNGProvider,
    build_provider,
)
from .search import WebSearchResult, search_web

__all__ = [
    "LABEL",
    "AllowedSource",
    "DuckDuckGoProvider",
    "FetchError",
    "FetchedPage",
    "ProviderError",
    "SearchResult",
    "SearXNGProvider",
    "WebEvidence",
    "WebSearchResult",
    "build_provider",
    "citation",
    "fetch_page",
    "find_allowed",
    "get_fresh",
    "is_fresh",
    "load_allowlist",
    "promotion_draft",
    "search_web",
    "should_search",
    "ttl_days",
]
