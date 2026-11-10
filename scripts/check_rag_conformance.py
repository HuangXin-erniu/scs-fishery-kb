#!/usr/bin/env python3
"""Machine-check the concrete RAG conformance items.

The human-readable matrix is docs/rag-conformance.md; this script enforces the
subset that can be checked mechanically: manifest fields, the atomic pointer,
the web allowlist and default, the acceptance thresholds and the no-tag policy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT

REQUIRED_MANIFEST = (
    "index_version",
    "code_commit",
    "embedding",
    "bm25",
    "chunks",
    "documents",
    "table_rows",
    "chunk_digest",
    "snapshot_manifest_sha256",
    "pipeline_config_sha256",
    "reranker",
)


def _check(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    checks: list[dict] = []

    allowlist_path = REPO_ROOT / "configs" / "web-sources.yaml"
    allowlist = (
        yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
        if allowlist_path.is_file()
        else {}
    )
    domains = [row for row in (allowlist.get("allowlist") or []) if row.get("domain")]
    _check(checks, "web allowlist present", len(domains) >= 10, f"{len(domains)} domains")
    _check(
        checks,
        "web allowlist hosts are bare",
        all("://" not in str(row.get("domain")) for row in domains),
    )

    interface = yaml.safe_load(
        (REPO_ROOT / "configs" / "interface.yaml").read_text(encoding="utf-8")
    )
    query = interface.get("query") or {}
    modes = list(query.get("modes") or [])
    _check(checks, "web default is off", query.get("web_default") in {"off", False})
    _check(checks, "kb_plus_web mode present", "kb_plus_web" in modes)
    _check(checks, "web_only mode absent", "web_only" not in modes)

    accept = yaml.safe_load(
        (REPO_ROOT / "configs" / "eval-accept.yaml").read_text(encoding="utf-8")
    )
    thresholds = accept.get("thresholds") or {}
    _check(
        checks,
        "acceptance thresholds present",
        len(thresholds) == 6,
        f"{len(thresholds)} lines",
    )
    _check(checks, "protocol v2 frozen", accept.get("protocol") == "v2")

    conformance = REPO_ROOT / "docs" / "rag-conformance.md"
    _check(checks, "conformance matrix present", conformance.is_file())
    if conformance.is_file():
        text = conformance.read_text(encoding="utf-8")
        _check(
            checks,
            "matrix covers 12 sections",
            all(f"§{index}" in text for index in range(1, 13)),
        )

    try:
        tags = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "tag"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        tags = ""
    _check(checks, "zero tags", tags == "", tags[:80])

    if args.data_root:
        index_root = Path(args.data_root).expanduser() / "v2" / "index"
        manifest_path = index_root / "manifest.json"
        _check(checks, "index manifest present", manifest_path.is_file())
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            missing = [key for key in REQUIRED_MANIFEST if key not in manifest]
            _check(checks, "manifest fields complete", not missing, ",".join(missing))
            _check(checks, "manifest has no fake reranker", manifest.get("reranker") is None)
        current = index_root / "current.json"
        _check(checks, "current pointer present", current.is_file())
        if current.is_file():
            pointer = json.loads(current.read_text(encoding="utf-8"))
            target = index_root / str(pointer.get("table") or "")
            _check(checks, "current pointer resolves", target.is_dir(), str(target))
    else:
        checks.append(
            {
                "name": "index manifest present",
                "ok": True,
                "detail": "skipped (no data root)",
            }
        )

    failed = [check for check in checks if not check["ok"]]
    if args.json:
        print(json.dumps({"checks": checks, "failed": len(failed)}, ensure_ascii=False, indent=2))
    else:
        for check in checks:
            print(f"{'ok ' if check['ok'] else 'BAD'} {check['name']} {check['detail']}")
        print(f"failed {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
