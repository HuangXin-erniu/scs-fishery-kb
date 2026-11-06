from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from ..web import _tls_context


class ProviderError(RuntimeError):
    """Raised when a search provider is unavailable or returns invalid data."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    rank: int


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]: ...


class SearXNGProvider:
    name = "searxng"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        language: str = "zh-CN",
        user_agent: str = "scs-fkb-web/1.0",
        opener: Callable[[urllib.request.Request, float], bytes] | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ProviderError("searxng_url must start with http:// or https://")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.language = language
        self.user_agent = user_agent
        self._opener = opener or self._default_opener

    def _default_opener(self, request: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout, context=_tls_context()) as response:
            return response.read()

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        params = urllib.parse.urlencode(
            {"q": query, "format": "json", "language": self.language, "safesearch": 1}
        )
        request = urllib.request.Request(
            f"{self.base_url}/search?{params}",
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        try:
            raw = self._opener(request, self.timeout)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - provider availability
            raise ProviderError(f"searxng.request_failed: {exc}") from exc
        rows = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ProviderError("searxng.invalid_response")
        results: list[SearchResult] = []
        for row in rows[:max_results]:
            if not isinstance(row, dict):
                continue
            url = str(row.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            results.append(
                SearchResult(
                    title=str(row.get("title") or "").strip(),
                    url=url,
                    snippet=str(row.get("content") or "").strip(),
                    rank=len(results) + 1,
                )
            )
        return results


class DuckDuckGoProvider:
    name = "ddgs"

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        region: str = "cn-zh",
        backend: str = "auto",
        retry_delay: float = 3.0,
    ) -> None:
        self.timeout = timeout
        self.region = region
        self.backend = backend
        self.retry_delay = retry_delay

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise ProviderError("ddgs is not installed; install requirements-rag.txt") from exc
        rows: list[dict] = []
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with DDGS(timeout=self.timeout) as client:
                    rows = list(
                        client.text(
                            query,
                            max_results=max_results,
                            region=self.region,
                            backend=self.backend,
                        )
                    )
                break
            except Exception as exc:  # noqa: BLE001 - provider availability
                last_error = exc
                if attempt == 0 and self.retry_delay > 0:
                    import time

                    time.sleep(self.retry_delay)
                    continue
                raise ProviderError(f"ddgs.request_failed: {exc}") from exc
        if not rows and last_error is not None:
            raise ProviderError(f"ddgs.request_failed: {last_error}") from last_error
        results: list[SearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = str(row.get("href") or row.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            results.append(
                SearchResult(
                    title=str(row.get("title") or "").strip(),
                    url=url,
                    snippet=str(row.get("body") or row.get("snippet") or "").strip(),
                    rank=len(results) + 1,
                )
            )
        return results


def build_provider(
    searxng_url: str = "",
    *,
    fallback: str = "ddgs",
    timeout: float = 15.0,
    backend: str = "auto",
) -> SearchProvider:
    if searxng_url:
        return SearXNGProvider(searxng_url, timeout=timeout)
    if fallback != "ddgs":
        raise ProviderError(f"unsupported search fallback: {fallback}")
    return DuckDuckGoProvider(timeout=timeout, backend=backend)


__all__ = [
    "DuckDuckGoProvider",
    "ProviderError",
    "SearchProvider",
    "SearchResult",
    "SearXNGProvider",
    "build_provider",
]
