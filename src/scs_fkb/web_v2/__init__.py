"""Ephemeral web evidence: allowlist, providers, fetch, cache and TTL.

The layer is optional and off by default. It never ingests into the corpus and
never decides whether a question is answerable.
"""

from .evidence import (
    LABEL,
    WebEvidence,
    citation,
    get_fresh,
    is_fresh,
    promotion_draft,
)
from .fetch import FetchedPage, FetchError, clean_text, fetch_page
from .policy import (
    MAX_LEADS,
    WEB_MODES,
    AllowedSource,
    WebConfig,
    find_allowed,
    load_allowlist,
    load_web_config,
    normalize_mode,
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
    "MAX_LEADS",
    "WEB_MODES",
    "AllowedSource",
    "DuckDuckGoProvider",
    "FetchError",
    "FetchedPage",
    "ProviderError",
    "SearchResult",
    "SearXNGProvider",
    "WebConfig",
    "WebEvidence",
    "WebSearchResult",
    "build_provider",
    "citation",
    "clean_text",
    "fetch_page",
    "find_allowed",
    "get_fresh",
    "is_fresh",
    "load_allowlist",
    "load_web_config",
    "normalize_mode",
    "promotion_draft",
    "search_web",
    "should_search",
    "ttl_days",
]
