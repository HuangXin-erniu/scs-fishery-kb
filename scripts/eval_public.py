#!/usr/bin/env python3
"""Deterministic public regression: retrieval, abstention, citations and KB resolution.

This set is derived from the public docs/questions.md samples. It is not the
private 512-question acceptance instrument and never reads its files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.kb_v2 import build_numbers, load_faq, load_terms_plain
from scs_fkb.service_v2.answer import build_service
from scs_fkb.service_v2.schemas import QueryResponse


def _load_set(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"empty public set: {path}")
    return entries


def _reachable(row: dict, registry_docs: set[str]) -> bool:
    """A row is measurable by corpus retrieval only if its expected document is registered."""
    if any(doc in registry_docs for doc in row.get("expected_docs") or []):
        return True
    prefix = str(row.get("expected_prefix") or "")
    return bool(prefix) and any(doc.startswith(prefix) for doc in registry_docs)


def _hit(result: QueryResponse, row: dict) -> bool:
    cited = {item.doc_id for item in result.citations}
    if not cited:
        return False
    expected = set(row.get("expected_docs") or [])
    prefix = str(row.get("expected_prefix") or "")
    if cited & expected:
        return True
    return bool(prefix) and any(doc.startswith(prefix) for doc in cited)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--set", default=str(REPO_ROOT / "configs" / "eval-public.yaml"))
    parser.add_argument("--task-id", default="P17-KB-210")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2

    os.environ.setdefault("SCS_FKB_WEB", "off")
    # The public regression is the historical dump-arm baseline; the standard
    # arm is measured by Track B, not here.
    os.environ.setdefault("SCS_FKB_ANSWER_MODE", "dump")
    service = build_service(data_root=args.data_root)
    rows = _load_set(Path(args.set))

    retrieval = [row for row in rows if row.get("type") != "abstain"]
    abstain = [row for row in rows if row.get("type") == "abstain"]
    hits = 0
    all_hits = 0
    abstain_ok = 0
    citation_rows = 0
    citation_ok = 0
    registry = getattr(service, "_registry", {})
    indexed_docs = {str(chunk.doc_id) for chunk in getattr(service.retriever, "chunks", []) or []}
    registry_docs = indexed_docs or set(registry)
    channel_rows = [
        str(row.get("id") or row["question"])
        for row in retrieval
        if not _reachable(row, registry_docs)
    ]
    reachable = [row for row in retrieval if _reachable(row, registry_docs)]
    for row in rows:
        result = service.query(row["question"], web="off")
        if row.get("type") == "abstain":
            abstain_ok += int(result.abstained)
        else:
            reached = _hit(result, row)
            all_hits += int(reached)
            if _reachable(row, registry_docs):
                hits += int(reached)
        if result.citations:
            citation_rows += 1
            if all(item.doc_id in registry for item in result.citations):
                citation_ok += 1

    playbooks = [item for item in service.playbooks if item.get("status") == "approved"]
    playbook_ok = 0
    for playbook in playbooks:
        result = service.query(str(playbook.get("title") or ""), web="off")
        if result.playbook is not None and result.playbook.id == playbook.get("id"):
            playbook_ok += 1

    faq = load_faq()
    terms = load_terms_plain()
    numbers = build_numbers(service.facts)
    term_ok = sum(
        1
        for item in terms
        if all(str(cite.get("doc") or "") in registry for cite in item.get("citations") or [])
    )
    number_ok = sum(1 for item in numbers if item["doc"] in registry)
    faq_ok = sum(
        1
        for item in faq
        if all(str(cite.get("doc") or "") in registry for cite in item.get("citations") or [])
    )

    metrics = {
        "questions": len(rows),
        "retrieval_rows": len(retrieval),
        "reachable_rows": len(reachable),
        "channel_rows": channel_rows,
        "recall_at_5": round(hits / len(reachable), 4) if reachable else 0.0,
        "recall_at_5_all": round(all_hits / len(retrieval), 4) if retrieval else 0.0,
        "abstain_rows": len(abstain),
        "abstain_accuracy": round(abstain_ok / len(abstain), 4) if abstain else 0.0,
        "citation_resolution": round(citation_ok / citation_rows, 4) if citation_rows else 0.0,
        "playbook_match": f"{playbook_ok}/{len(playbooks)}",
        "faq_resolution": f"{faq_ok}/{len(faq)}",
        "term_resolution": f"{term_ok}/{len(terms)}",
        "number_resolution": f"{number_ok}/{len(numbers)}",
    }
    report = f"""# Public regression

- Source: `{Path(args.set).name}` (public samples, not the private instrument)
- Questions: {metrics["questions"]} ({metrics["retrieval_rows"]} retrieval, \
{metrics["abstain_rows"]} abstention)

| Metric | Value |
|---|---:|
| Anchor recall@5 (reachable rows) | {metrics["recall_at_5"]} |
| Anchor recall@5 (all rows) | {metrics["recall_at_5_all"]} |
| Channel rows (expected document not registered) | {len(metrics["channel_rows"])} |
| Abstention accuracy | {metrics["abstain_accuracy"]} |
| Citation resolution | {metrics["citation_resolution"]} |
| Playbook match | {metrics["playbook_match"]} |
| FAQ citation resolution | {metrics["faq_resolution"]} |
| Term citation resolution | {metrics["term_resolution"]} |
| Number source resolution | {metrics["number_resolution"]} |
"""
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.run_root:
        directory = Path(args.run_root).expanduser() / args.task_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "public-regression.md").write_text(report, encoding="utf-8")
        (directory / "public-regression.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"report: {directory / 'public-regression.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
