#!/usr/bin/env python3
"""Build the parallel v2 ingestion store and a private verification report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.ingest_v2 import build_v2


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _anchors(rows: list[dict[str, Any]], docs: set[str]) -> set[tuple[str, int, str]]:
    return {
        (str(row.get("doc_id")), int(row.get("page") or 0), str(row.get("section") or ""))
        for row in rows
        if str(row.get("doc_id")) in docs
    }


def _report(result: Any, data_root: Path, pipeline_docs: list[str]) -> str:
    v1 = _anchors(_rows(data_root / "processed" / "chunks.jsonl"), set(pipeline_docs))
    v2 = _anchors(_rows(data_root / "v2" / "processed" / "chunks.jsonl"), set(pipeline_docs))
    snapshots = json.loads((data_root / "v2" / "snapshots.json").read_text(encoding="utf-8"))
    summary = snapshots.get("summary") or {}
    lost = sorted(v1 - v2)
    extra = sorted(v2 - v1)
    lines = [
        "# P10-ING-137 build report",
        "",
        f"- Data root: `{data_root.as_posix()}`",
        f"- Documents: {result.documents}",
        f"- Parent chunks: {result.parents}",
        f"- Child chunks: {result.chunks}",
        f"- Pages: {result.pages}",
        f"- Build id: `{result.build_id}`",
        f"- Snapshot manifest: `{result.snapshot_manifest_sha256}`",
        f"- Rebuilt: {', '.join(result.rebuilt) or 'none'}",
        f"- Skipped: {', '.join(result.skipped) or 'none'}",
        f"- Removed: {', '.join(result.removed) or 'none'}",
        f"- Snapshot sources: {summary.get('sources', 0)}",
        f"- Snapshot files: {summary.get('files', 0)}",
        f"- Snapshot bytes: {summary.get('bytes', 0)}",
        "",
        "## Parsers",
        "",
        "| Document | Parser |",
        "|---|---|",
    ]
    for doc_id in sorted(result.parsers):
        lines.append(f"| `{doc_id}` | `{result.parsers[doc_id]}` |")

    lines.extend(
        [
            "",
            "## Anchor comparison against v1",
            "",
            f"- v1 anchors for the configured documents: {len(v1)}",
            f"- v2 anchors for the configured documents: {len(v2)}",
            f"- Lost anchors: {len(lost)}",
            f"- Extra anchors: {len(extra)}",
        ]
    )
    for doc_id, page, section in lost[:20]:
        lines.append(f"- lost: `{doc_id}` page={page} section={section}")
    for doc_id, page, section in extra[:20]:
        lines.append(f"- extra: `{doc_id}` page={page} section={section}")

    lines.extend(
        [
            "",
            "## Quarantine",
            "",
            *(
                [f"- `{row['doc_id']}`: {row['reason']}" for row in result.quarantined]
                or ["- none"]
            ),
            "",
            "## Snapshot audit",
            "",
            f"- Sources: {len(result.counts)} configured documents",
            "- The full 63-source snapshot summary is in `v2/snapshots.json`; "
            "single-file sources are hash-verified and directory sources carry a file manifest.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/corpus.yaml")
    parser.add_argument("--pipeline", default="configs/pipeline.yaml")
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--report", default=None)
    parser.add_argument("--no-snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    data_root = Path(args.data_root).expanduser().resolve()
    result = build_v2(
        Path(args.config),
        Path(args.pipeline),
        data_root,
        refresh_snapshots=not args.no_snapshot,
    )
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            f"v2 build {result.build_id}: {result.documents} docs, "
            f"{result.parents} parents, {result.chunks} children, "
            f"rebuilt={len(result.rebuilt)} skipped={len(result.skipped)} "
            f"quarantined={len(result.quarantined)}"
        )
    if args.run_root or args.report:
        if args.report:
            report_path = Path(args.report)
        else:
            report_path = Path(args.run_root).expanduser() / "P10-ING-137" / "build.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline = yaml.safe_load(Path(args.pipeline).read_text(encoding="utf-8"))
        report_path.write_text(
            _report(result, data_root, list(pipeline["documents"])),
            encoding="utf-8",
        )
        print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
