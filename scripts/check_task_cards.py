#!/usr/bin/env python3
"""Validate task cards against approved facts and registered playbooks."""

from __future__ import annotations

import argparse
import sys

from scs_fkb.facts import load_all
from scs_fkb.knowledge_v2.playbooks import load_playbooks
from scs_fkb.knowledge_v2.task_cards import load_task_cards, validate_task_cards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", default="configs/knowledge/task-cards.yaml")
    args = parser.parse_args(argv)
    cards = load_task_cards(args.cards)
    errors = validate_task_cards(cards, facts=load_all(), playbooks=load_playbooks())
    approved = sum(1 for card in cards if card.get("status") == "approved")
    print(f"task cards {len(cards)} approved {approved} errors {len(errors)}")
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
