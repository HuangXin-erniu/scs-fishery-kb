from __future__ import annotations

import hashlib
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .parsers import ParseError, parse_source

CARD_ID = re.compile(r"WEB-[A-Z0-9-]+")
REQUIRED_CARD = (
    "id",
    "topic",
    "title",
    "publisher",
    "url",
    "fetched_at",
    "sha256",
    "content_type",
    "license",
    "sensitivity",
    "source_class",
    "file",
    "status",
    "excerpt",
)


class WebError(RuntimeError):
    """Raised when a web config or a card is malformed."""


def load_web_sources(path: Path) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.is_file():
        raise WebError(f"web.sources.missing: {source_path}")
    data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise WebError(f"web.sources.invalid: {source_path}")
    allowlist = data.get("allowlist")
    if not isinstance(allowlist, list) or not allowlist:
        raise WebError("web.sources.invalid: allowlist is empty")
    for entry in allowlist:
        if not isinstance(entry, dict) or not entry.get("domain"):
            raise WebError(f"web.sources.invalid: bad allowlist entry {entry!r}")
        if not entry.get("publisher") or entry.get("tier") not in {"A", "B", "C"}:
            raise WebError(
                f"web.sources.invalid: entry {entry.get('domain')!r} needs publisher and tier"
            )
    topics = data.get("topics")
    if not isinstance(topics, dict) or not topics:
        raise WebError("web.sources.invalid: topics are empty")
    refresh = data.get("refresh")
    if not isinstance(refresh, dict):
        raise WebError("web.sources.invalid: refresh settings are missing")
    for key in ("timeout_seconds", "rate_limit_seconds", "max_bytes"):
        if not isinstance(refresh.get(key), (int, float)):
            raise WebError(f"web.sources.invalid: refresh.{key} must be numeric")
    return data


def load_cards(path: Path) -> dict[str, Any]:
    card_path = Path(path)
    if not card_path.is_file():
        raise WebError(f"web.cards.missing: {card_path}")
    data = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise WebError(f"web.cards.invalid: {card_path}")
    cards = data.get("cards")
    if not isinstance(cards, list):
        raise WebError("web.cards.invalid: cards is not a list")
    seen: set[str] = set()
    for card in cards:
        validate_card(card)
        if card["id"] in seen:
            raise WebError(f"web.cards.invalid: duplicate id {card['id']}")
        seen.add(card["id"])
    return data


def validate_card(card: Any) -> None:
    if not isinstance(card, dict):
        raise WebError(f"web.cards.invalid: card is not a mapping: {card!r}")
    for key in REQUIRED_CARD:
        if key not in card:
            raise WebError(f"web.cards.invalid: {card.get('id', '<unknown>')} missing {key}")
    if not CARD_ID.fullmatch(str(card["id"])):
        raise WebError(f"web.cards.invalid: bad id {card['id']!r}")
    if urllib.parse.urlsplit(str(card["url"])).scheme != "https":
        raise WebError(f"web.cards.invalid: {card['id']} url is not https")
    if card["status"] not in {"ok", "failed"}:
        raise WebError(f"web.cards.invalid: {card['id']} status {card['status']!r}")
    if card["source_class"] != "reference":
        raise WebError(f"web.cards.invalid: {card['id']} source_class must be reference")


def is_allowed(url: str, allowlist: list[dict[str, Any]]) -> tuple[bool, str]:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        return False, f"scheme {parts.scheme!r} is not https"
    host = (parts.hostname or "").lower()
    for entry in allowlist:
        domain = str(entry["domain"]).lower()
        if host == domain or host.endswith("." + domain):
            return True, domain
    return False, f"host {host!r} is not allowlisted"


def _tls_context() -> ssl.SSLContext:
    try:
        return ssl.create_default_context()
    except ssl.SSLError:
        fallback = Path("/etc/ssl/cert.pem")
        if fallback.is_file():
            return ssl.create_default_context(cafile=str(fallback))
        raise


def fetch(url: str, *, timeout: float, max_bytes: int, user_agent: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout, context=_tls_context()) as response:
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise WebError(f"web.fetch.too_large: {url} exceeds {max_bytes} bytes")
        return payload, str(response.headers.get("Content-Type") or "")


def _extract(payload: bytes, content_type: str, url: str, cache_dir: Path) -> tuple[str, str]:
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        suffix, fmt = ".pdf", "pdf"
    else:
        suffix, fmt = ".html", "html"
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = cache_dir / f"fetch{suffix}"
    temporary.write_bytes(payload)
    try:
        parsed = parse_source(temporary, fmt)
    finally:
        temporary.unlink(missing_ok=True)
    text = "\n".join(page.text for page in parsed.pages).strip()
    if not text:
        raise WebError(f"web.extract.empty: {url}")
    return text, fmt


def refresh(
    cards_path: Path,
    sources_path: Path,
    cache_root: Path,
    *,
    fetcher: Callable[[str], tuple[bytes, str]] | None = None,
    topic: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    sources = load_web_sources(sources_path)
    data = load_cards(cards_path)
    settings = sources["refresh"]
    allowlist = sources["allowlist"]
    stamp = (now or datetime.now(UTC)).replace(microsecond=0).isoformat()
    cache = Path(cache_root)
    if fetcher is None:

        def fetcher(url: str) -> tuple[bytes, str]:
            return fetch(
                url,
                timeout=float(settings["timeout_seconds"]),
                max_bytes=int(settings["max_bytes"]),
                user_agent=str(settings["user_agent"]),
            )

    results: list[dict[str, Any]] = []
    for card in data["cards"]:
        if topic and card["topic"] != topic:
            continue
        allowed, reason = is_allowed(str(card["url"]), allowlist)
        if not allowed:
            card.update({"status": "failed", "error": reason})
            results.append({"id": card["id"], "status": "failed", "error": reason})
            continue
        try:
            payload, content_type = fetcher(str(card["url"]))
            text, fmt = _extract(payload, content_type, str(card["url"]), cache / card["id"])
            digest = hashlib.sha256(payload).hexdigest()
            target = cache / card["id"] / "text.txt"
            target.write_text(text, encoding="utf-8")
            card.update(
                {
                    "fetched_at": stamp,
                    "sha256": digest,
                    "content_type": content_type or fmt,
                    "file": str(target.relative_to(cache)),
                    "status": "ok",
                    "excerpt": " ".join(text.split())[:300],
                    "error": "",
                }
            )
            results.append({"id": card["id"], "status": "ok", "sha256": digest})
        except (WebError, ParseError, urllib.error.URLError, OSError) as exc:
            card.update({"status": "failed", "error": str(exc)})
            results.append({"id": card["id"], "status": "failed", "error": str(exc)})
        delay = float(settings["rate_limit_seconds"])
        if delay > 0 and results and results[-1]["status"] == "ok":
            time.sleep(delay)

    data["cards"] = sorted(data["cards"], key=lambda item: item["id"])
    Path(cards_path).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    ok = sum(1 for row in results if row["status"] == "ok")
    return {"cards": results, "ok": ok, "failed": len(results) - ok}
