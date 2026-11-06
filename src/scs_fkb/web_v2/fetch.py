from __future__ import annotations

import hashlib
import re
import tempfile
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from ..web import _tls_context
from .policy import AllowedSource, find_allowed

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FetchError(RuntimeError):
    """Raised when an allowlisted page cannot be fetched or decoded."""


@dataclass(frozen=True)
class FetchedPage:
    url: str
    final_url: str
    status: int
    content_type: str
    content_hash: str
    title: str
    text: str
    allowed: AllowedSource


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "td", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1
        elif tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "td", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def _plain_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def _pdf_text(body: bytes) -> str:
    from ..parsers import ParseError, parse_source

    with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
        handle.write(body)
        handle.flush()
        try:
            parsed = parse_source(Path(handle.name), "pdf")
        except ParseError as exc:
            raise FetchError(f"web.pdf_parse_failed: {exc}") from exc
    return "\n".join(page.text for page in parsed.pages).strip()


def _extract_text(body: str, content_type: str) -> str:
    if "html" not in content_type.lower() and "<html" not in body.lower():
        return body.strip()
    try:
        import trafilatura

        extracted = trafilatura.extract(
            body,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        if extracted:
            return extracted.strip()
    except Exception:  # noqa: BLE001 - optional extractor
        pass
    return _plain_text(body)


def _default_opener(
    request: urllib.request.Request, timeout: float
) -> tuple[int, Mapping, bytes, str]:
    with urllib.request.urlopen(request, timeout=timeout, context=_tls_context()) as response:
        body = response.read()
        return (
            int(response.status),
            dict(response.headers),
            body,
            str(response.geturl()),
        )


def fetch_page(
    url: str,
    allowlist: list[AllowedSource],
    *,
    timeout: float = 15.0,
    max_bytes: int = 4_000_000,
    user_agent: str = "scs-fkb-web/1.0",
    opener: Callable[[urllib.request.Request, float], tuple[int, Mapping, bytes, str]]
    | None = None,
) -> FetchedPage:
    allowed = find_allowed(url, allowlist)
    if allowed is None:
        raise FetchError(f"web.not_allowlisted: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        status, headers, body, final_url = (opener or _default_opener)(request, timeout)
    except Exception as exc:  # noqa: BLE001 - network failure is recorded by the caller
        raise FetchError(f"web.fetch_failed: {url}: {exc}") from exc
    if status >= 400:
        raise FetchError(f"web.http_{status}: {url}")
    final_allowed = find_allowed(final_url, allowlist)
    if final_allowed is None:
        raise FetchError(f"web.redirect_not_allowlisted: {final_url}")
    if len(body) > max_bytes:
        raise FetchError(f"web.too_large: {url}")
    content_type = str(headers.get("Content-Type") or headers.get("content-type") or "")
    if "pdf" in content_type.lower() or final_url.lower().endswith(".pdf"):
        text = _pdf_text(body)
        return FetchedPage(
            url=url,
            final_url=final_url,
            status=status,
            content_type=content_type or "application/pdf",
            content_hash=hashlib.sha256(body).hexdigest(),
            title=final_url.rsplit("/", 1)[-1],
            text=text,
            allowed=final_allowed,
        )
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = body.decode("gb18030")
        except UnicodeDecodeError as exc:
            raise FetchError(f"web.encoding: {url}") from exc
    title_match = TITLE_RE.search(decoded)
    title = " ".join(title_match.group(1).split()) if title_match else ""
    text = _extract_text(decoded, content_type)
    return FetchedPage(
        url=url,
        final_url=final_url,
        status=status,
        content_type=content_type,
        content_hash=hashlib.sha256(body).hexdigest(),
        title=title,
        text=text,
        allowed=final_allowed,
    )


__all__ = ["FetchError", "FetchedPage", "fetch_page"]
