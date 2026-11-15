#!/usr/bin/env python3
"""Discover specific document URLs from a candidate's section page.

Reads `configs/candidates.yaml`, fetches each selected candidate homepage and
extracts same-site links whose anchor text matches practical keywords. It writes
a shortlist under the run root and never captures, registers or promotes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scs_fkb.candidates import load_candidates

DEFAULT_KEYWORDS = (
    "休渔",
    "禁渔",
    "台风",
    "预警",
    "海浪",
    "风暴潮",
    "赤潮",
    "海况",
    "气象",
    "灾害",
    "应急",
    "安全",
    "渔具",
    "网目",
    "捕捞",
    "许可",
    "证书",
    "补贴",
    "油价",
    "市场",
    "价格",
    "港口",
    "渔港",
    "日志",
    "船员",
    "培训",
    "标准",
)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) scs-fkb-discover/0.1"
DATE_RE = re.compile(r"20\d{2}[-/年]?(?:0?[1-9]|1[0-2])")


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = ""
            self._text = []
            for key, value in attrs:
                if key == "href" and value:
                    self._href = value.strip()

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            text = re.sub(r"\s+", " ", " ".join(self._text)).strip()
            self.links.append((self._href, text))
            self._href = ""
            self._text = []


def _same_site(base_host: str, host: str) -> bool:
    base = base_host.lower().lstrip(".")
    candidate = host.lower().lstrip(".")
    return candidate == base or candidate.endswith("." + base)


def extract_links(
    html: str,
    base_url: str,
    *,
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
    limit: int = 20,
) -> list[dict]:
    """Return scored same-site links whose anchor text carries a keyword."""
    parser = _LinkParser()
    parser.feed(html)
    base = urlparse(base_url)
    rows: list[dict] = []
    seen: set[str] = set()
    for href, text in parser.links:
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if not _same_site(base.hostname or "", parsed.hostname):
            continue
        if parsed.path.lower().endswith((".jpg", ".png", ".gif", ".zip", ".rar")):
            continue
        clean = url.split("#", 1)[0]
        if clean in seen:
            continue
        seen.add(clean)
        score = sum(2 for keyword in keywords if keyword in text)
        if DATE_RE.search(text) or DATE_RE.search(parsed.path):
            score += 2
        if len(text) >= 8:
            score += 1
        if score <= 0:
            continue
        rows.append({"url": clean, "text": text[:120], "host": parsed.hostname, "score": score})
    rows.sort(key=lambda row: (-row["score"], row["url"]))
    return rows[:limit]


def _fetch(url: str, timeout: float) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as handle:
        path = Path(handle.name)
    try:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "--max-time",
                str(int(timeout)),
                "-A",
                UA,
                "-o",
                str(path),
                "-w",
                "%{http_code}",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        status = int(result.stdout.strip() or 0)
        body = path.read_bytes()[:2_000_000].decode("utf-8", "ignore")
        return status, body
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return 0, f"<!-- fetch error: {type(exc).__name__} -->"
    finally:
        path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--candidates", default="configs/candidates.yaml")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--keywords", default="")
    args = parser.parse_args(argv)
    if not args.run_root:
        print("error: set SCS_FKB_RUN_ROOT or pass --run-root", file=sys.stderr)
        return 2
    keywords = (
        tuple(item.strip() for item in (args.keywords or "").split(",") if item.strip())
        or DEFAULT_KEYWORDS
    )
    candidates = load_candidates(args.candidates)
    selected = (
        candidates
        if args.all
        else [item for item in candidates if item.get("id") in set(args.candidate_id)]
    )
    if not selected:
        print("error: no candidate selected (use --candidate-id or --all)", file=sys.stderr)
        return 2
    output = Path(args.run_root).expanduser().resolve() / "discovery"
    output.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for candidate in selected:
        candidate_id = str(candidate.get("id") or "")
        url = str(candidate.get("url") or "")
        status, html = _fetch(url, args.timeout)
        rows = (
            extract_links(html, url, keywords=keywords, limit=args.limit) if status == 200 else []
        )
        (output / f"{candidate_id}.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        summary.append({"id": candidate_id, "url": url, "status": status, "links": len(rows)})
        print(f"{candidate_id} status={status} links={len(rows)}", flush=True)
        time.sleep(0.5)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"summary: {output / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
