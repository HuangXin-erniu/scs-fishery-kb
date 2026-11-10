#!/usr/bin/env python3
"""Build or update the LanceDB index over the v2 child chunks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from scs_fkb.index_v2 import build_index_v2, rollback_index
from scs_fkb.index_v2.embedding import build_encoder
from scs_fkb.index_v2.store import prune_versions


def _report(result, data_root: Path) -> str:
    lines = [
        "# Index build report",
        "",
        f"- Data root: `{data_root.as_posix()}`",
        f"- Index version: `{result.index_version}`",
        f"- Model: `{result.model}` ({result.dim} dims)",
        f"- Documents: {result.documents}",
        f"- Child chunks: {result.chunks}",
        f"- Table rows: {result.table_rows}",
        f"- Build seconds: {result.build_seconds}",
        f"- Peak RSS MB: {result.peak_rss_mb}",
        f"- No-op: {result.no_op}",
        f"- Rebuilt: {', '.join(result.rebuilt) or 'none'}",
        f"- Removed: {', '.join(result.removed) or 'none'}",
        f"- Version path: `{result.version_path}`",
        f"- Manifest: `{result.manifest_path}`",
        "",
        "The index is built from `v2/processed/chunks.jsonl`; it does not change "
        "the v1 index or the answer path.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--rollback", action="store_true", help="switch to the previous version")
    parser.add_argument("--prune", action="store_true", help="keep only the last two versions")
    parser.add_argument("--keep", type=int, default=2)
    parser.add_argument("--report", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    root = Path(args.data_root).expanduser().resolve()
    if args.rollback:
        try:
            rolled = rollback_index(root)
        except Exception as exc:  # noqa: BLE001 - report the reason and stop
            print(f"rollback failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(rolled, ensure_ascii=False, indent=2))
        return 0
    if args.prune:
        removed = prune_versions(root, keep=args.keep)
        print(json.dumps({"removed": removed}, ensure_ascii=False))
        return 0
    encoder = build_encoder(args.model, cache_dir=str(root / "embeddings" / "models"))
    result = build_index_v2(root, encoder, force=args.force)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            f"index {result.index_version}: {result.chunks} chunks, {result.table_rows} rows, "
            f"{result.build_seconds}s, no_op={result.no_op}, "
            f"rebuilt={len(result.rebuilt)} removed={len(result.removed)}"
        )
    if args.run_root or args.report:
        path = (
            Path(args.report)
            if args.report
            else Path(args.run_root).expanduser() / "P17-RAG-211" / "build.md"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_report(result, root), encoding="utf-8")
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
