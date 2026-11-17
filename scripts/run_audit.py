#!/usr/bin/env python3
"""Stream the canonical audit artifact through D1-D11 and emit the ledger."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.audit.detectors import run_all  # noqa: E402
from scs_fkb.audit.schema import AuditRecord  # noqa: E402
from scs_fkb.registry import load_registry  # noqa: E402


def _chunk_index(path: Path) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            section = str(row.get("section", ""))
            page = row.get("page")
            if not section and page:
                section = f"p.{page}"
            index[str(row["doc_id"])].append((section, str(row.get("text", ""))))
    return dict(index)


def _doc_meta() -> dict[str, dict[str, Any]]:
    registry = load_registry()
    out: dict[str, dict[str, Any]] = {}
    for doc_id, entry in registry.items():
        effective = entry.get("effective") or {}
        out[doc_id] = {
            "level": entry.get("level", ""),
            "effective_from": effective.get("from", ""),
            "effective_to": effective.get("to", ""),
            "year": entry.get("year", ""),
            "publisher": entry.get("publisher", ""),
        }
    return out


def _load_records(path: Path) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                records.append(
                    AuditRecord(
                        **{
                            key: raw.get(key)
                            for key in AuditRecord.__dataclass_fields__
                            if key in raw
                        }
                    )
                )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--config", default=str(ROOT / "configs" / "audit.yaml"))
    parser.add_argument("--detectors", default="", help="comma-separated subset, e.g. D1,D2,D3,D4")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data_root = Path(args.data_root)
    chunk_index = _chunk_index(data_root / "v2" / "processed" / "chunks.jsonl")
    doc_meta = _doc_meta()
    records = _load_records(Path(args.answers))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "defect-ledger.csv"
    rows: list[dict[str, str]] = []
    by_dim: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    stage_counts: dict[str, Counter[str]] = defaultdict(Counter)
    detector_counts: Counter[str] = Counter()
    for record in records:
        findings = run_all(record, chunk_index, doc_meta, config)
        if args.detectors:
            allowed = {part.strip().upper() for part in args.detectors.split(",") if part.strip()}
            findings = [finding for finding in findings if finding.detector in allowed]
        for finding in findings:
            detector_counts[finding.detector] += 1
            row = finding.to_row()
            row.update(
                {
                    "source": record.source,
                    "theme": record.theme,
                    "gap_status": record.gap_status,
                    "stage": record.pipeline_stage,
                    "question": record.question[:120],
                }
            )
            rows.append(row)
            by_dim[("source", record.source, finding.detector)][finding.severity] += 1
            by_dim[("theme", record.theme, finding.detector)][finding.severity] += 1
            by_dim[("stage", record.pipeline_stage, finding.detector)][finding.severity] += 1
            stage_counts[record.pipeline_stage][finding.detector] += 1
    fieldnames = [
        "id",
        "detector",
        "severity",
        "sentence",
        "evidence_pointer",
        "chunk_id",
        "rule_version",
        "source",
        "theme",
        "gap_status",
        "stage",
        "question",
    ]
    with ledger_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / "defect-distribution.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["dimension", "value", "detector", "S1", "S2", "S3"])
        for (dimension, value, detector), counts in sorted(by_dim.items()):
            writer.writerow(
                [
                    dimension,
                    value,
                    detector,
                    counts.get("S1", 0),
                    counts.get("S2", 0),
                    counts.get("S3", 0),
                ]
            )
    with (out_dir / "stage-attribution.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stage", "detector", "count"])
        for stage, counts in sorted(stage_counts.items()):
            for detector, count in sorted(counts.items()):
                writer.writerow([stage, detector, count])
    print(f"records={len(records)} findings={len(rows)}")
    print("by detector:", dict(sorted(detector_counts.items())))
    print("ledger:", ledger_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
