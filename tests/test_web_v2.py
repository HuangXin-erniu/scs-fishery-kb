from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from scs_fkb.web_v2 import (
    AllowedSource,
    FetchedPage,
    FetchError,
    ProviderError,
    SearchResult,
    SearXNGProvider,
    citation,
    fetch_page,
    find_allowed,
    load_allowlist,
    promotion_draft,
    search_web,
    should_search,
    ttl_days,
)


def _allowlist(tmp_path: Path) -> list[AllowedSource]:
    path = tmp_path / "web-sources.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "allowlist": [
                    {"domain": "www.gov.cn", "publisher": "中国政府网", "tier": "A"},
                    {"domain": "moa.gov.cn", "publisher": "农业农村部", "tier": "A"},
                    {"domain": "gd.gov.cn", "publisher": "广东省人民政府", "tier": "A"},
                    {"domain": "gov.cn", "publisher": "地方政府网站", "tier": "C"},
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return load_allowlist(path)


class FakeProvider:
    name = "fake"

    def __init__(self, results: list[SearchResult], error: Exception | None = None) -> None:
        self.results = results
        self.error = error

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        if self.error:
            raise self.error
        return self.results[:max_results]


def _page(
    url: str, text: str = "2026年南海伏季休渔时间为5月1日至8月16日。", digest: str = "a" * 64
) -> FetchedPage:
    return FetchedPage(
        url=url,
        final_url=url,
        status=200,
        content_type="text/html",
        content_hash=digest,
        title="测试页面",
        text=text,
        allowed=AllowedSource(domain="moa.gov.cn", publisher="农业农村部", tier="A"),
    )


def test_allowlist_exact_subdomain_and_https(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)
    assert find_allowed("https://www.moa.gov.cn/a", allowlist)
    assert find_allowed("https://moa.gov.cn/a", allowlist)
    assert find_allowed("http://www.moa.gov.cn/a", allowlist) is None
    assert find_allowed("https://example.org/a", allowlist) is None
    assert find_allowed("https://www.gov.cn/a", allowlist).tier == "A"
    municipal = find_allowed("https://www.zhifu.gov.cn/a", allowlist)
    assert municipal is not None and municipal.tier == "C"


def test_ttl_and_trigger_policy() -> None:
    assert ttl_days("warning") == 7
    assert ttl_days("rule") == 30
    assert ttl_days("definition") == 90
    assert ttl_days("statistics") == 365
    assert should_search("2026年南海伏季休渔时间", nature="rule")[0] is True
    assert should_search("历史沿革", nature="history")[0] is False
    assert should_search("某渔场历史渔汛", nature="history", local_abstained=True)[0] is True
    assert should_search("随便问问", nature="definition", explicit=True)[0] is True


def test_search_filters_allowlist_and_caches(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)
    results = [
        SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1),
        SearchResult("子域", "https://yyj.moa.gov.cn/b", "摘要", 2),
        SearchResult("越界", "https://example.org/c", "摘要", 3),
        SearchResult("非 https", "http://www.moa.gov.cn/d", "摘要", 4),
    ]
    calls: list[str] = []

    def fetcher(url: str, allowed: list[AllowedSource]) -> FetchedPage:
        calls.append(url)
        return _page(url, digest=(str(len(calls)) * 64)[:64])

    now = datetime(2026, 11, 6, tzinfo=UTC)
    first = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=allowlist,
        provider=FakeProvider(results),
        data_root=tmp_path / "data",
        max_results=5,
        fetcher=fetcher,
        now=now,
    )
    assert first.triggered is True
    assert len(first.evidences) == 2
    assert len(first.dropped) == 2
    assert len(calls) == 2
    assert (tmp_path / "data" / "v2" / "web-cache" / "index.json").is_file()

    second = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=allowlist,
        provider=FakeProvider(results),
        data_root=tmp_path / "data",
        max_results=5,
        fetcher=fetcher,
        now=now + timedelta(days=1),
    )
    assert second.cached == 2
    assert len(calls) == 2

    third = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=allowlist,
        provider=FakeProvider(results),
        data_root=tmp_path / "data",
        max_results=5,
        fetcher=fetcher,
        now=now + timedelta(days=31),
    )
    assert third.cached == 0
    assert len(calls) == 4
    assert citation(third.evidences[0]).startswith("[WEB:")


def test_search_reports_provider_failure(tmp_path: Path) -> None:
    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=FakeProvider([], ProviderError("offline")),
        data_root=tmp_path / "data",
        fetcher=lambda url, allowed: _page(url),
    )
    assert result.failures
    assert result.evidences == []


def test_fetch_page_rejects_non_allowlisted_and_redirect(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)
    with pytest.raises(FetchError, match="not_allowlisted"):
        fetch_page("https://example.org/a", allowlist)

    def opener(request, timeout):
        return (
            200,
            {"Content-Type": "text/html"},
            b"<title>T</title><p>Body</p>",
            "https://example.org/x",
        )

    with pytest.raises(FetchError, match="redirect_not_allowlisted"):
        fetch_page("https://www.moa.gov.cn/a", allowlist, opener=opener)


def test_fetch_page_extracts_text_and_hash(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)

    def opener(request, timeout):
        body = "<html><title>休渔通告</title><body><p>南海区休渔时间。</p></body></html>".encode()
        return 200, {"Content-Type": "text/html; charset=utf-8"}, body, "https://www.moa.gov.cn/a"

    page = fetch_page("https://www.moa.gov.cn/a", allowlist, opener=opener)
    assert page.title == "休渔通告"
    assert "休渔" in page.text
    assert len(page.content_hash) == 64


def test_promotion_draft_is_not_written(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    results = [SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1)]
    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=FakeProvider(results),
        data_root=data_root,
        fetcher=lambda url, allowed: _page(url),
    )
    draft = promotion_draft(result.evidences[0], today=datetime(2026, 11, 6).date())
    assert draft["status"] == "open"
    assert draft["url"] == "https://www.moa.gov.cn/a"
    assert not (tmp_path / "configs" / "candidates.yaml").exists()


def test_searxng_provider_parses_json() -> None:
    payload = b'{"results":[{"title":"T","url":"https://www.moa.gov.cn/a","content":"C"}]}'

    def opener(request, timeout):
        return payload

    provider = SearXNGProvider("http://127.0.0.1:8888", opener=opener)
    results = provider.search("休渔")
    assert results[0].url == "https://www.moa.gov.cn/a"
