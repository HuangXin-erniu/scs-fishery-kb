#!/usr/bin/env python3
"""Audit the v4 -> v5 source-register derivation.

The register file stays at ``source_record_schema: 4`` until an entry is next
edited; the loader upgrades it in memory. This script reports what the upgrade
derives, so the migration is auditable. It never rewrites ``configs/corpus.yaml``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.registry import (
    INGEST_TIERS,
    PRACTICAL_DOMAINS,
    SOURCE_CLASSES,
    normalize_entry,
    validate_entry,
)


def _file_schema(path: Path) -> int:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"register is not a mapping: {path}")
    try:
        return int(data.get("source_record_schema", 3))
    except (TypeError, ValueError):
        return 3


def _sources(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list) or not sources:
        raise SystemExit(f"no sources in {path}")
    return [source for source in sources if isinstance(source, dict)]


def audit(path: Path) -> dict[str, Any]:
    sources = _sources(path)
    file_schema = _file_schema(path)
    normalized = [normalize_entry(source) for source in sources]
    errors: list[str] = []
    for source in normalized:
        errors.extend(validate_entry(source))
    return {
        "path": str(path),
        "sources": len(sources),
        "source_record_schema_input": sorted(
            {str(source.get("source_record_schema", file_schema)) for source in sources}
        ),
        "source_record_schema_output": 5,
        "errors": errors,
        "source_classes": dict(
            Counter(str(source.get("source_class") or "") for source in normalized)
        ),
        "authority_scores": dict(
            Counter(int((source.get("authority") or {}).get("score") or 0) for source in normalized)
        ),
        "ingest_tiers": dict(
            Counter(str((source.get("ingest") or {}).get("tier") or "") for source in normalized)
        ),
        "ttl_days": dict(
            Counter(
                int((source.get("currency") or {}).get("ttl_days") or 0) for source in normalized
            )
        ),
        "practical_tagged": sum(
            1 for source in normalized if (source.get("practical") or {}).get("domain")
        ),
        "license_evidence_url": sum(
            1
            for source in normalized
            if str((source.get("license_evidence") or {}).get("url") or "").strip()
        ),
        "known_source_classes": sorted(SOURCE_CLASSES),
        "known_ingest_tiers": sorted(INGEST_TIERS),
        "known_practical_domains": sorted(PRACTICAL_DOMAINS),
    }


def _report(data: dict[str, Any]) -> str:
    lines = [
        "# Source schema v5 migration audit",
        "",
        f"- Register: `{data['path']}`",
        f"- Sources: {data['sources']}",
        f"- Input schema: {', '.join(data['source_record_schema_input'])}",
        f"- Output schema: {data['source_record_schema_output']}",
        f"- Errors: {len(data['errors'])}",
        f"- Practical-tagged sources: {data['practical_tagged']}",
        f"- License-evidence URL present: {data['license_evidence_url']}",
        "",
        "## Ingest tiers",
        "",
        "| Tier | Count |",
        "|---|---:|",
    ]
    for tier, count in sorted(data["ingest_tiers"].items()):
        lines.append(f"| {tier or '(empty)'} | {count} |")
    lines.extend(["", "## TTL days", "", "| TTL | Count |", "|---|---:|"])
    for ttl, count in sorted(data["ttl_days"].items()):
        lines.append(f"| {ttl or '(empty)'} | {count} |")
    if data["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in data["errors"][:50])
    lines.append("")
    lines.append(
        "The register file was not modified. The loader derives these fields in "
        "memory; a future edit of an entry may persist them explicitly."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", default="configs/corpus.yaml")
    parser.add_argument("--out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = audit(Path(args.register))
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        report = _report(data)
        if args.out:
            path = Path(args.out).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
            print(f"report: {path}")
        else:
            print(report)
    return 0 if not data["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
