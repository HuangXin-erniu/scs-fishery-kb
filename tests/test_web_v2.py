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
    build_provider,
    citation,
    clean_text,
    fetch_page,
    find_allowed,
    load_allowlist,
    load_web_config,
    promotion_draft,
    search_web,
    should_search,
    ttl_days,
)
from scs_fkb.web_v2.providers import FallbackProvider

BODY = (
    "南海区伏季休渔时间为5月1日12时至8月16日12时。除钓具外的所有作业类型，"
    "以及为捕捞渔船配套服务的捕捞辅助船，均纳入休渔管理。违反规定的，依照"
    "渔业法查处。"
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
        self.calls = 0

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.results[:max_results]


def _page(url: str, text: str = BODY, digest: str = "a" * 64) -> FetchedPage:
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
    assert should_search("某渔场历史渔汛", nature="history")[0] is False
    assert should_search("某渔场历史渔汛", nature="history", local_abstained=True)[0] is True
    assert should_search("某渔场历史渔汛", nature="history", stale_evidence=True) == (
        True,
        "stale_evidence",
    )
    assert should_search("随便问问", nature="definition", explicit=True)[0] is True


def test_mode_off_never_calls_the_provider(tmp_path: Path) -> None:
    provider = FakeProvider([SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1)])
    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=provider,
        data_root=tmp_path / "data",
        mode="off",
    )
    assert result.triggered is False
    assert result.reason == "mode_off"
    assert provider.calls == 0


def test_auto_mode_skips_when_no_trigger(tmp_path: Path) -> None:
    provider = FakeProvider([SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1)])
    result = search_web(
        "网目尺寸怎么规定",
        nature="definition",
        allowlist=_allowlist(tmp_path),
        provider=provider,
        data_root=tmp_path / "data",
        mode="auto",
    )
    assert result.triggered is False
    assert provider.calls == 0


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
        max_evidences=2,
        spacing_seconds=0,
        fetcher=fetcher,
        now=now,
    )
    assert first.triggered is True
    assert len(first.evidences) == 2
    assert len(first.dropped) == 2
    assert len(calls) == 2
    assert (tmp_path / "data" / "web-cache" / "index.json").is_file()

    second = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=allowlist,
        provider=FakeProvider(results),
        data_root=tmp_path / "data",
        max_results=5,
        max_evidences=2,
        spacing_seconds=0,
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
        max_evidences=2,
        spacing_seconds=0,
        fetcher=fetcher,
        now=now + timedelta(days=31),
    )
    assert third.cached == 0
    assert len(calls) == 4
    assert citation(third.evidences[0]).startswith("[WEB:")


def test_leads_are_capped_and_spaced(tmp_path: Path) -> None:
    results = [
        SearchResult(f"页面{index}", f"https://www.moa.gov.cn/{index}", "摘要", index)
        for index in range(1, 6)
    ]
    sleeps: list[float] = []
    calls: list[str] = []

    def fetcher(url: str, allowed: list[AllowedSource]) -> FetchedPage:
        calls.append(url)
        return _page(url, digest=(str(len(calls)) * 64)[:64])

    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=FakeProvider(results),
        data_root=tmp_path / "data",
        max_results=5,
        max_evidences=2,
        spacing_seconds=2,
        fetcher=fetcher,
        sleeper=sleeps.append,
    )
    assert len(result.evidences) == 2
    assert len(calls) == 2
    assert sleeps == [2]


def test_search_reports_provider_failure(tmp_path: Path) -> None:
    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=FakeProvider([], ProviderError("offline")),
        data_root=tmp_path / "data",
        spacing_seconds=0,
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


def test_fetch_page_rejects_oversize_and_binary(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)

    def big(request, timeout):
        return 200, {"Content-Type": "text/html"}, b"x" * 20, "https://www.moa.gov.cn/a"

    with pytest.raises(FetchError, match="too_large"):
        fetch_page("https://www.moa.gov.cn/a", allowlist, max_bytes=10, opener=big)

    def image(request, timeout):
        return 200, {"Content-Type": "image/png"}, b"x", "https://www.moa.gov.cn/a"

    with pytest.raises(FetchError, match="unsupported_content_type"):
        fetch_page("https://www.moa.gov.cn/a", allowlist, opener=image)


def test_fetch_page_extracts_text_and_hash(tmp_path: Path) -> None:
    allowlist = _allowlist(tmp_path)

    def opener(request, timeout):
        body = "<html><title>休渔\u200b通告</title><body><p>南海区休渔时间。</p></body></html>"
        return (
            200,
            {"Content-Type": "text/html; charset=utf-8"},
            body.encode(),
            ("https://www.moa.gov.cn/a"),
        )

    page = fetch_page("https://www.moa.gov.cn/a", allowlist, opener=opener)
    assert page.title == "休渔通告"
    assert "休渔" in page.text
    assert "\u200b" not in page.title
    assert len(page.content_hash) == 64


def test_clean_text_strips_invisible_and_control_characters() -> None:
    assert clean_text("a\u200bb\u202ec\x00d") == "abcd"


def test_promotion_draft_is_not_written(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    results = [SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1)]
    result = search_web(
        "2026年南海伏季休渔 最新",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=FakeProvider(results),
        data_root=data_root,
        spacing_seconds=0,
        fetcher=lambda url, allowed: _page(url),
    )
    draft = promotion_draft(result.evidences[0], today=datetime(2026, 11, 6).date())
    assert draft["status"] == "open"
    assert draft["url"] == "https://www.moa.gov.cn/a"
    assert not (tmp_path / "configs" / "candidates.yaml").exists()


def test_load_web_config_reads_limits(tmp_path: Path) -> None:
    path = tmp_path / "web-sources.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "allowlist": [{"domain": "moa.gov.cn", "publisher": "农业农村部", "tier": "A"}],
                "provider": {"searxng_url": "http://127.0.0.1:8888", "max_results": 8},
                "limits": {"max_evidences": 2, "spacing_seconds": 3, "snippet_chars": 200},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    config = load_web_config(path)
    assert config.domain_count == 1
    assert config.settings["max_evidences"] == 2
    assert config.settings["spacing_seconds"] == 3.0
    assert config.settings["max_results"] == 8


def test_searxng_provider_parses_json() -> None:
    payload = b'{"results":[{"title":"T","url":"https://www.moa.gov.cn/a","content":"C"}]}'

    def opener(request, timeout):
        return payload

    provider = SearXNGProvider("http://127.0.0.1:8888", opener=opener)
    results = provider.search("休渔")
    assert results[0].url == "https://www.moa.gov.cn/a"


class _FixedProvider:
    def __init__(self, name: str, results: list[SearchResult], error: Exception | None = None):
        self.name = name
        self.results = results
        self.error = error
        self.calls = 0

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.results


def test_fallback_provider_prefers_primary() -> None:
    primary = _FixedProvider("primary", [SearchResult("P", "https://www.moa.gov.cn/a", "", 1)])
    fallback = _FixedProvider("fallback", [SearchResult("F", "https://www.moa.gov.cn/b", "", 1)])
    result = FallbackProvider(primary, fallback).search("休渔")
    assert result[0].title == "P"
    assert fallback.calls == 0


def test_fallback_provider_uses_fallback_on_empty_or_error() -> None:
    empty = _FixedProvider("primary", [])
    fallback = _FixedProvider("fallback", [SearchResult("F", "https://www.moa.gov.cn/b", "", 1)])
    assert FallbackProvider(empty, fallback).search("休渔")[0].title == "F"

    broken = _FixedProvider("primary", [], ProviderError("offline"))
    assert FallbackProvider(broken, fallback).search("休渔")[0].title == "F"


def test_fallback_provider_raises_when_both_fail() -> None:
    primary = _FixedProvider("primary", [], ProviderError("p"))
    fallback = _FixedProvider("fallback", [], ProviderError("f"))
    with pytest.raises(ProviderError, match="p.*f"):
        FallbackProvider(primary, fallback).search("休渔")


def test_build_provider_returns_combined_when_searxng_is_configured() -> None:
    provider = build_provider("http://127.0.0.1:8888")
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.primary, SearXNGProvider)
    assert isinstance(build_provider(""), type(build_provider("")))


class _ScriptedProvider:
    name = "scripted"

    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        self.queries.append(query)
        if "site:" in query:
            return [SearchResult("官方", "https://www.moa.gov.cn/a", "摘要", 1)]
        return [SearchResult("越界", "https://example.org/a", "摘要", 1)]


def test_site_hint_retries_when_no_allowlisted_result(tmp_path: Path) -> None:
    provider = _ScriptedProvider()
    result = search_web(
        "广东省2026年伏季休渔",
        nature="rule",
        allowlist=_allowlist(tmp_path),
        provider=provider,
        data_root=tmp_path / "data",
        mode="on",
        site_hint="gov.cn",
        spacing_seconds=0,
        fetcher=lambda url, allowed: _page(url),
    )
    assert len(provider.queries) == 2
    assert "site:gov.cn" in provider.queries[1]
    assert len(result.evidences) == 1
    assert result.evidences[0].domain == "www.moa.gov.cn"
