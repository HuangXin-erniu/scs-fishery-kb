#!/usr/bin/env python3
"""Provision-fact promotion experiment helper.

Snapshots the deterministic fact-lead signature for a local acceptance dataset,
compares two snapshots and flips only the named draft facts. It never writes
question text: snapshots contain document ids and sections only.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from scs_fkb.facts import DEFAULT_FACTS_DIR
from scs_fkb.service_v2.answer import build_service

TRIAL_IDS = [
    "FACT-PROV-006",
    "FACT-PROV-007",
    "FACT-PROV-009",
    "FACT-PROV-014",
    "FACT-PROV-020",
    "FACT-PROV-029",
    "FACT-PROV-038",
    "FACT-PROV-048",
    "FACT-PROV-053",
    "FACT-PROV-058",
    "FACT-PROV-068",
    "FACT-PROV-071",
]


def _paths(directory: Path | str) -> list[Path]:
    return sorted(Path(directory).glob("*.yaml"))


def set_status(directory: Path | str, ids: list[str], status: str) -> int:
    """Set the status of the named facts, preserving every other field and order."""
    wanted = set(ids)
    changed = 0
    for path in _paths(directory):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        dirty = False
        for fact in data.get("facts") or []:
            if fact.get("id") in wanted and fact.get("status") != status:
                fact["status"] = status
                changed += 1
                dirty = True
        if dirty:
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
    return changed


def _signature(service: Any, question: str) -> str:
    from scs_fkb.retrieve_v2 import plan_query

    plan = plan_query(question, today=date.today())
    hits = service.retriever.search_queries([question], top_k=5)
    lead = service._fact_lead(question, hits, plan.nature)
    if lead is None:
        return ""
    return f"{lead[1].doc_id}|{lead[1].section}"


def snapshot(data_root: str, dataset: Path, out: Path) -> dict[str, Any]:
    service = build_service(data_root=data_root)
    service._llm = None
    questions = [
        json.loads(line)["question"]
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    signatures = [_signature(service, question) for question in questions]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"count": len(signatures), "signatures": signatures}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"count": len(signatures), "with_lead": sum(1 for item in signatures if item)}


def compare(old_path: Path, new_path: Path) -> dict[str, Any]:
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    old_rows = old.get("signatures") or []
    new_rows = new.get("signatures") or []
    if len(old_rows) != len(new_rows):
        raise SystemExit("snapshot lengths differ")
    changed = [index for index, (a, b) in enumerate(zip(old_rows, new_rows, strict=True)) if a != b]
    added = sum(1 for index in changed if not old_rows[index] and new_rows[index])
    removed = sum(1 for index in changed if old_rows[index] and not new_rows[index])
    replaced = len(changed) - added - removed
    return {
        "count": len(old_rows),
        "changed": len(changed),
        "added": added,
        "removed": removed,
        "replaced": replaced,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts-dir", default=str(DEFAULT_FACTS_DIR))
    sub = parser.add_subparsers(dest="command", required=True)

    promote = sub.add_parser("promote")
    promote.add_argument("--status", default="approved")
    promote.add_argument("--ids", nargs="*", default=TRIAL_IDS)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--data-root", required=True)
    snap.add_argument("--dataset", required=True)
    snap.add_argument("--out", required=True)

    diff = sub.add_parser("compare")
    diff.add_argument("--old", required=True)
    diff.add_argument("--new", required=True)

    args = parser.parse_args(argv)
    if args.command == "promote":
        changed = set_status(args.facts_dir, args.ids, args.status)
        print(json.dumps({"changed": changed, "ids": args.ids}, ensure_ascii=False))
        return 0
    if args.command == "snapshot":
        result = snapshot(args.data_root, Path(args.dataset), Path(args.out))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    result = compare(Path(args.old), Path(args.new))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
