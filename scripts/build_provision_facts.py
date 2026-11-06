#!/usr/bin/env python3
"""Generate 120 reviewable provision facts from the indexed corpus.

The facts are deliberately drafts: they are section-level pointers with exact
evidence, not approved atomic values. A human review can promote the useful ones.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

from scs_fkb.config import DEFAULT_CONFIG
from scs_fkb.facts import normalize
from scs_fkb.registry import load_registry
from scs_fkb.store import load_chunks


def _topic(doc_type: str) -> str:
    if doc_type in {"law", "regulation", "notice"}:
        return "policy"
    if doc_type in {"standard", "operations"}:
        return "gear"
    return "stats"


def _question_class(doc_type: str) -> str:
    if doc_type in {"law", "regulation", "notice"}:
        return "status"
    if doc_type in {"standard", "operations"}:
        return "procedure"
    return "definition"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--registry", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", default="configs/facts/provisions.yaml")
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    data_root = Path(args.data_root).expanduser().resolve()
    registry = load_registry(args.registry)
    chunks, _manifest = load_chunks(data_root)
    today = date.fromisoformat(args.today)

    grouped: dict[str, list] = {}
    for chunk in chunks:
        if len(normalize(chunk.text)) < 20:
            continue
        if chunk.doc_id not in registry:
            continue
        grouped.setdefault(chunk.doc_id, []).append(chunk)

    selected = []
    for doc_id in sorted(grouped):
        section_chunks = [chunk for chunk in grouped[doc_id] if chunk.section.strip()]
        selected.extend(
            sorted(section_chunks, key=lambda chunk: (chunk.page, chunk.char_start))[:5]
        )
    chosen = {chunk.chunk_id for chunk in selected}
    for doc_id in sorted(grouped):
        for chunk in sorted(grouped[doc_id], key=lambda item: (item.page, item.char_start)):
            if len(selected) >= args.count:
                break
            if chunk.chunk_id in chosen:
                continue
            selected.append(chunk)
            chosen.add(chunk.chunk_id)
        if len(selected) >= args.count:
            break
    selected = selected[: args.count]
    if len(selected) < args.count:
        print(
            f"error: only {len(selected)} eligible chunks for {args.count} facts",
            file=sys.stderr,
        )
        return 1

    subjects: set[str] = set()
    facts = []
    for index, chunk in enumerate(selected, start=1):
        source = registry[chunk.doc_id]
        title = str(source.get("title") or chunk.doc_id)
        section = chunk.section
        section_label = section or f"片段{index}"
        subject = f"{title} {section_label}".strip()
        if subject in subjects:
            subject = f"{subject} #{index}"
        subjects.add(subject)
        evidence = normalize(chunk.text)[:240]
        if len(evidence) < 20:
            evidence = normalize(chunk.text)[:400]
        facts.append(
            {
                "id": f"FACT-PROV-{index:03d}",
                "kind": "provision",
                "topic": _topic(str(source.get("type") or "")),
                "question_class": _question_class(str(source.get("type") or "")),
                "subject": subject,
                "predicate": "条文要点",
                "value": evidence,
                "evidence": evidence,
                "source": {
                    "doc": chunk.doc_id,
                    **({"section": section} if section else {}),
                    "sha256": str(source.get("hash") or ""),
                },
                "status": "draft",
                "confidence": "medium",
                "as_of": today.isoformat(),
                "review_due": (today + timedelta(days=90)).isoformat(),
                "jurisdiction": str(source.get("jurisdiction") or "national"),
                "reviewer": "auto:provision-v1",
                "extraction": "section-provision-v1",
            }
        )
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "updated_at": today.isoformat(), "facts": facts},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(facts)} provision facts to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
