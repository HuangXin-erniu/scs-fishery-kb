#!/usr/bin/env python3
"""Capture one public source into the local data root and print its provenance.

The register keeps metadata and hashes only; the raw snapshot stays under
``$SCS_FKB_DATA_ROOT/raw/<source-id>/``. This helper refuses non-HTTPS URLs and
hosts outside the official allowlist, never overwrites an existing snapshot
unless ``--force`` is passed, and prints the provenance block that
``configs/corpus.yaml`` expects.

Usage:
    python scripts/capture_source.py --url URL --source-id ID \
        [--data-root DIR] [--slug NAME] [--force] [--print-record]
"""

from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO_ROOT / "configs" / "web-sources.yaml"
FALLBACK_HOSTS = (
    "gov.cn",
    "moa.gov.cn",
    "msa.gov.cn",
    "npc.gov.cn",
    "spp.gov.cn",
    "jcy.gov.cn",
    "mofcom.gov.cn",
    "cas.cn",
    "schinafish.cn",
    "pices.int",
    "mdpi.com",
    "nih.gov",
)


def _configured_hosts(path: Path = DEFAULT_ALLOWLIST) -> tuple[str, ...]:
    """Load the official-host allowlist from configs/web-sources.yaml."""
    if not path.is_file():
        return ()
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - capture must still work with the fallback
        return ()
    entries = data.get("allowlist") if isinstance(data, dict) else None
    hosts: list[str] = []
    for entry in entries or []:
        if isinstance(entry, dict):
            domain = str(entry.get("domain") or "").strip().lower()
            if domain:
                hosts.append(domain)
    return tuple(hosts)


ALLOWED_HOSTS = tuple(dict.fromkeys(FALLBACK_HOSTS + _configured_hosts()))
EXTENSIONS = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
SLUG_RE = re.compile(r"[^a-z0-9]+")


class CaptureError(RuntimeError):
    """Raised when a source cannot be captured within the capture policy."""


def host_allowed(host: str) -> bool:
    host = host.lower().strip(".")
    return any(host == item or host.endswith("." + item) for item in ALLOWED_HOSTS)


def check_url(url: str, *, allow_http: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        if not (
            allow_http
            and parsed.scheme == "http"
            and parsed.hostname
            and parsed.hostname.endswith(".gov.cn")
        ):
            raise CaptureError(f"refusing non-HTTPS URL: {url}")
    if not parsed.hostname or not host_allowed(parsed.hostname):
        raise CaptureError(f"host is not allowlisted: {parsed.hostname}")
    return parsed.hostname


def slugify(value: str, fallback: str = "source") -> str:
    slug = SLUG_RE.sub("-", unquote(value).lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or fallback)[:80]


def extension_for(content_type: str, url: str) -> str:
    media = (content_type or "").split(";")[0].strip().lower()
    if media in EXTENSIONS:
        return EXTENSIONS[media]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".html", ".htm", ".pdf", ".txt", ".docx"}:
        return ".html" if suffix == ".htm" else suffix
    guessed = mimetypes.guess_extension(media) if media else None
    return guessed or ".bin"


def snapshot_path(source_id: str, slug: str, extension: str) -> str:
    return f"raw/{source_id}/{slug}{extension}"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Capture:
    source_id: str
    url: str
    path: Path
    relative: str
    sha256: str
    bytes: int
    mime: str
    unchanged: bool
    transport: str = "https"

    def provenance(self, *, document_no: str = "", published_at: str = "") -> str:
        lines = [
            "provenance:",
            f"  url: {self.url}",
        ]
        if document_no:
            lines.append(f"  document_no: {document_no}")
        if published_at:
            lines.append(f"  published_at: '{published_at}'")
        lines += [
            f"  retrieved_at: '{date.today().isoformat()}'",
            f"  sha256: {self.sha256}",
            f"  bytes: {self.bytes}",
            f"  mime: {self.mime}",
            f"  snapshot_path: {self.relative}",
            f"  transport: {self.transport}",
            "  fetched_by: scripts/capture_source.py",
        ]
        if self.transport != "https":
            lines.append("  transport_note: publisher serves no HTTPS; plaintext capture recorded")
        return "\n".join(lines)


def _open(request, timeout: float):
    """Use the project TLS helper when available (system-bundle fallback)."""
    try:
        from scs_fkb.web_v2.net import open_url

        return open_url(request, timeout)
    except ImportError:
        import urllib.request

        return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310


def fetch(url: str, *, allow_http: bool = False) -> tuple[bytes, str]:
    import urllib.error
    import urllib.request

    check_url(url, allow_http=allow_http)
    timeout = float(os.environ.get("SCS_FKB_CAPTURE_TIMEOUT", "120"))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) scs-fkb/0.1",
            "Accept": "text/html,application/pdf,*/*;q=0.8",
        },
    )
    try:
        with _open(request, timeout) as response:
            return response.read(), str(response.headers.get("Content-Type") or "")
    except urllib.error.HTTPError as exc:
        raise CaptureError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise CaptureError(f"network error for {url}: {exc.reason}") from exc


def capture(
    url: str,
    source_id: str,
    data_root: Path,
    *,
    slug: str = "",
    force: bool = False,
    allow_http: bool = False,
) -> Capture:
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,40}", source_id):
        raise CaptureError(f"invalid source id: {source_id}")
    payload, content_type = fetch(url, allow_http=allow_http)
    transport = "http" if urlparse(url).scheme == "http" else "https"
    if not payload:
        raise CaptureError(f"empty response for {url}")
    extension = extension_for(content_type, url)
    name = slug or slugify(Path(urlparse(url).path).stem or source_id, fallback=source_id.lower())
    relative = snapshot_path(source_id, name, extension)
    target = data_root.expanduser() / relative
    if target.exists() and not force:
        existing = target.read_bytes()
        if sha256_bytes(existing) != sha256_bytes(payload):
            raise CaptureError(
                f"{target} already exists with different bytes; pass --force to replace"
            )
        return Capture(
            source_id=source_id,
            url=url,
            path=target,
            relative=relative,
            sha256=sha256_bytes(existing),
            bytes=len(existing),
            mime=content_type.split(";")[0].strip() or "application/octet-stream",
            unchanged=True,
            transport=transport,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return Capture(
        source_id=source_id,
        url=url,
        path=target,
        relative=relative,
        sha256=sha256_bytes(payload),
        bytes=len(payload),
        mime=content_type.split(";")[0].strip() or "application/octet-stream",
        unchanged=False,
        transport=transport,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--slug", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="allow plain HTTP for allowlisted .gov.cn hosts (recorded in provenance)",
    )
    parser.add_argument("--document-no", default="")
    parser.add_argument("--published-at", default="")
    parser.add_argument("--print-record", action="store_true", help="print the YAML block")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("set --data-root or SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    try:
        result = capture(
            args.url,
            args.source_id,
            Path(args.data_root),
            slug=args.slug,
            force=args.force,
            allow_http=args.allow_http,
        )
    except CaptureError as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 2
    state = "unchanged" if result.unchanged else "captured"
    print(
        f"{state} {result.source_id}: {result.bytes} bytes sha256 {result.sha256[:12]} "
        f"{result.mime} transport {result.transport}"
    )
    if args.print_record:
        print(
            result.provenance(
                document_no=args.document_no,
                published_at=args.published_at,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
