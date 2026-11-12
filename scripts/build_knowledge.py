#!/usr/bin/env python3
"""Build task cards and canonical answers from approved playbooks and FAQ.

Default is a read-only report under the run root. `--write-configs` explicitly
updates the public knowledge configs; the generated cards are drafts and still
need a human wording review.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from scs_fkb.facts import load_all
from scs_fkb.kb_v2.faq import load_faq
from scs_fkb.knowledge_v2.answers import (
    DEFAULT_ANSWERS,
    build_from_faq,
    load_answers,
    validate_answers,
    write_answers,
)
from scs_fkb.knowledge_v2.playbooks import load_playbooks
from scs_fkb.knowledge_v2.task_cards import (
    DEFAULT_TASK_CARDS,
    build_from_playbooks,
    load_task_cards,
    validate_task_cards,
    write_task_cards,
)
from scs_fkb.registry import load_registry


def _gaps(data_root: Path | None) -> list[dict[str, Any]]:
    if data_root is None:
        return []
    path = data_root / "gaps.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _gap_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clusters: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        clusters[
            (
                str(row.get("nature") or "general"),
                str(row.get("domain") or "general"),
                str(row.get("reason") or "unknown"),
            )
        ] += 1
    return {
        "total": len(rows),
        "clusters": [
            {"nature": key[0], "domain": key[1], "reason": key[2], "count": value}
            for key, value in sorted(clusters.items(), key=lambda item: -item[1])
        ],
        "recent": [str(row.get("question") or "") for row in rows[-10:]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--write-configs", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    facts = load_all()
    playbooks = load_playbooks()
    faq = load_faq()
    cards = build_from_playbooks(playbooks, facts)
    card_errors = validate_task_cards(cards, facts=facts, playbooks=playbooks)
    answers = build_from_faq(faq)
    registry = load_registry()
    answer_errors = validate_answers(answers, registry=registry)
    gaps = _gaps(Path(args.data_root).expanduser() if args.data_root else None)
    summary = {
        "date": date.today().isoformat(),
        "facts": len(facts),
        "playbooks": len(playbooks),
        "faq": len(faq),
        "task_cards": len(cards),
        "task_card_errors": card_errors,
        "canonical_answers": len(answers),
        "answer_errors": answer_errors,
        "gaps": _gap_summary(gaps),
        "task_card_statuses": dict(Counter(str(card.get("status")) for card in cards)),
        "answer_statuses": dict(Counter(str(entry.get("status")) for entry in answers)),
        "existing_task_cards": len(load_task_cards()) if DEFAULT_TASK_CARDS.is_file() else 0,
        "existing_answers": len(load_answers()) if DEFAULT_ANSWERS.is_file() else 0,
    }
    if args.write_configs:
        if card_errors or answer_errors:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            print("refusing to write invalid configs", file=os.sys.stderr)
            return 1
        write_task_cards(cards)
        write_answers(answers)
        summary["written"] = [str(DEFAULT_TASK_CARDS), str(DEFAULT_ANSWERS)]
    if args.report:
        path = Path(args.report).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"facts={summary['facts']} playbooks={summary['playbooks']} "
            f"task_cards={summary['task_cards']} answers={summary['canonical_answers']} "
            f"gap_rows={summary['gaps']['total']} errors="
            f"{len(card_errors) + len(answer_errors)}"
        )
        if args.report:
            print(f"report: {path}")
    return 0 if not (card_errors or answer_errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())
