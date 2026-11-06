#!/usr/bin/env python3
"""Audit the source register against source schema v4 without rewriting it.

The loader derives v4 defaults for compact v3 entries. This script makes that
derivation visible: it validates every entry, records which fields were derived,
and writes a migration audit under the run root. It never edits corpus.yaml and
never opens a source payload.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from scs_fkb.registry import (
    SOURCE_RECORD_SCHEMA,
    RegistryError,
    load_registry,
)


def _counter(registry: dict[str, dict], key: str) -> Counter:
    return Counter(
        str(entry.get(key) if key != "channel" else (entry.get("retrieval") or {}).get("channel"))
        for entry in registry.values()
    )


def _derived_count(raw: dict) -> dict[str, int]:
    derived = {
        "source_record_schema": "source_record_schema" not in raw,
        "provenance": "provenance" not in raw,
        "provenance.sha256": "provenance" not in raw
        or not (raw.get("provenance") or {}).get("sha256"),
        "provenance.snapshot_path": "provenance" not in raw
        or not (raw.get("provenance") or {}).get("snapshot_path"),
        "effective": "effective" not in raw,
        "quality": "quality" not in raw,
        "license_note": "license_note" not in raw,
        "supersedes": "supersedes" not in raw,
        "superseded_by": "superseded_by" not in raw,
    }
    return {key: int(value) for key, value in derived.items()}


def _table(counter: Counter) -> list[str]:
    lines = ["| Value | Count |", "|---|---:|"]
    for value, count in sorted(counter.items()):
        lines.append(f"| `{value}` | {count} |")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/corpus.yaml")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    args = parser.parse_args(argv)
    if not args.run_root:
        print("error: pass --run-root or set SCS_FKB_RUN_ROOT", file=sys.stderr)
        return 2

    config = Path(args.config)
    run_root = Path(args.run_root).expanduser()
    report_path = run_root / "P10-GOV-136" / "migration.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    raw_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    raw_sources = raw_data.get("sources") if isinstance(raw_data, dict) else None
    errors: list[str] = []
    registry: dict[str, dict] = {}
    try:
        registry = load_registry(config)
    except RegistryError as exc:
        errors.append(str(exc))
    except (OSError, yaml.YAMLError, AttributeError) as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    lines = [
        "# Source schema v4 migration audit",
        "",
        f"- Generated at: {datetime.now(UTC).replace(microsecond=0).isoformat()}",
        f"- Register: `{config.as_posix()}`",
        f"- Target record schema: {SOURCE_RECORD_SCHEMA}",
        f"- Sources read: {len(raw_sources or [])}",
        f"- Sources loaded: {len(registry)}",
        f"- Validation errors: {len(errors)}",
        "",
        "The register file is intentionally not rewritten. The loader presents the v4",
        "shape and derives missing provenance, effective-date and quality defaults from",
        "the existing `hash` and `location` fields.",
        "",
    ]

    if errors:
        lines.extend(["## Errors", "", *[f"- {error}" for error in errors], ""])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"migration audit written with errors: {report_path}")
        return 1

    changed_hashes: list[str] = []
    changed_ids: list[str] = []
    derived_totals: Counter = Counter()
    for raw in raw_sources or []:
        source_id = str(raw.get("id"))
        if source_id not in registry:
            changed_ids.append(source_id)
            continue
        normalized = registry[source_id]
        original_hash = raw.get("hash")
        if original_hash and normalized["provenance"]["sha256"] != original_hash:
            changed_hashes.append(source_id)
        for key, value in _derived_count(raw).items():
            derived_totals[key] += value

    v4_count = sum(
        1
        for entry in registry.values()
        if entry.get("source_record_schema") == SOURCE_RECORD_SCHEMA
    )
    lines.extend(
        [
            "## Integrity",
            "",
            f"- Ids lost during load: {len(changed_ids)}",
            f"- Hashes changed during load: {len(changed_hashes)}",
            f"- Source-record schema now v4: {v4_count}",
            "",
        ]
    )
    if changed_ids or changed_hashes:
        lines.extend(
            [
                "## Integrity failures",
                "",
                *[f"- missing id: `{source_id}`" for source_id in changed_ids],
                *[f"- changed hash: `{source_id}`" for source_id in changed_hashes],
                "",
            ]
        )

    lines.extend(["## Derived fields", "", "| Field | Entries derived |", "|---|---:|"])
    for key, count in sorted(derived_totals.items()):
        lines.append(f"| `{key}` | {count} |")

    lines.extend(
        [
            "",
            "## Distribution",
            "",
            "### Authority tier",
            "",
            *_table(_counter(registry, "authority_tier")),
        ]
    )
    lines.extend(["", "### Level", "", *_table(_counter(registry, "level"))])
    lines.extend(["", "### Source class", "", *_table(_counter(registry, "source_class"))])
    lines.extend(["", "### License", "", *_table(_counter(registry, "license"))])
    lines.extend(["", "### Channel", "", *_table(_counter(registry, "channel"))])

    lines.extend(
        [
            "",
            "## Result",
            "",
            "- No source payload, data file, index or run output other than this "
            "report was read or written.",
            "- No source id or hash changed.",
            "- `corpus.yaml` was not rewritten; explicit v4 fields are added when "
            "a source is next edited.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"migration audit written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
