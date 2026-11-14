"""Task cards: a short, persona-specific procedure with cited facts.

A task card is generated from an approved playbook and may be edited by hand.
Every step names at least one approved fact, so a card cannot outrun the evidence
layer. Cards are not playbooks and do not replace the source text.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ..config import REPO_ROOT
from ..facts import load_all

DEFAULT_TASK_CARDS = REPO_ROOT / "configs" / "knowledge" / "task-cards.yaml"
TASK_ID = re.compile(r"TASK-[A-Z]+-\d{3}")
PERSONAS = frozenset({"captain", "crew", "owner", "enforcement", "extension", "general"})
STATUSES = frozenset({"draft", "approved", "retired"})
REGION_LABEL = {"national": "全国", "provincial": "省级", "municipal": "市级"}
PERSONA_CODE = {
    "captain": "CAPTAIN",
    "crew": "CREW",
    "owner": "OWNER",
    "enforcement": "ENFORCEMENT",
    "extension": "EXTENSION",
    "general": "GENERAL",
}


class TaskCardError(RuntimeError):
    """Raised when a task-card file is malformed or unsupported."""


def load_task_cards(path: Path | str = DEFAULT_TASK_CARDS) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise TaskCardError(f"task cards not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    cards = data.get("cards") if isinstance(data, dict) else None
    if not isinstance(cards, list):
        raise TaskCardError(f"task cards is not a list: {source}")
    return cards


def _fact_map(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(fact.get("id")): fact for fact in facts}


def validate_task_cards(
    cards: list[dict[str, Any]],
    *,
    facts: list[dict[str, Any]] | None = None,
    playbooks: list[dict[str, Any]] | None = None,
) -> list[str]:
    approved = _fact_map(facts or load_all())
    playbook_ids = {str(item.get("id")) for item in (playbooks or [])}
    errors: list[str] = []
    seen: set[str] = set()
    for card in cards:
        identifier = str(card.get("id") or "<unknown>")
        if not TASK_ID.fullmatch(identifier):
            errors.append(f"{identifier}: id must match TASK-<PERSONA>-<NNN>")
        if identifier in seen:
            errors.append(f"{identifier}: duplicate id")
        seen.add(identifier)
        persona = card.get("persona")
        if persona not in PERSONAS:
            errors.append(f"{identifier}: persona {persona!r} not in {sorted(PERSONAS)}")
        if not str(card.get("title") or "").strip():
            errors.append(f"{identifier}: missing title")
        status = card.get("status")
        if status not in STATUSES:
            errors.append(f"{identifier}: status {status!r} not in {sorted(STATUSES)}")
        steps = card.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{identifier}: steps must be a non-empty list")
            continue
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                errors.append(f"{identifier}: step {index} is not a mapping")
                continue
            if not str(step.get("text") or "").strip():
                errors.append(f"{identifier}: step {index} has no text")
            fact_ids = step.get("facts")
            if not isinstance(fact_ids, list) or not fact_ids:
                errors.append(f"{identifier}: step {index} has no facts")
                continue
            for fact_id in fact_ids:
                fact = approved.get(str(fact_id))
                if fact is None:
                    errors.append(f"{identifier}: step {index} names unknown fact {fact_id!r}")
                elif fact.get("status") != "approved":
                    errors.append(f"{identifier}: step {index} names non-approved fact {fact_id!r}")
        source = card.get("source")
        if not isinstance(source, dict) or not str(source.get("id") or "").strip():
            errors.append(f"{identifier}: missing source")
        elif str(source.get("kind") or "") == "playbook" and playbook_ids:
            if str(source.get("id")) not in playbook_ids:
                errors.append(
                    f"{identifier}: source playbook {source.get('id')!r} is not registered"
                )
    return errors


def build_from_playbooks(
    playbooks: list[dict[str, Any]],
    facts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Turn approved playbooks into draft task cards; a human still reviews them."""
    approved = _fact_map(facts or load_all())
    counters: dict[str, int] = {}
    cards: list[dict[str, Any]] = []
    for playbook in playbooks:
        if playbook.get("status") != "approved":
            continue
        persona = str(playbook.get("persona") or "general")
        code = PERSONA_CODE.get(persona, "GENERAL")
        steps: list[dict[str, Any]] = []
        fact_ids: list[str] = []
        for step in playbook.get("steps") or []:
            if not isinstance(step, dict):
                continue
            step_facts = [
                str(fact_id)
                for fact_id in step.get("facts") or []
                if str(fact_id) in approved and approved[str(fact_id)].get("status") == "approved"
            ]
            if not step_facts:
                continue
            text = str(step.get("action") or "").strip()
            detail = str(step.get("detail") or "").strip()
            if detail:
                text = f"{text}：{detail}" if text else detail
            steps.append({"text": text, "facts": step_facts})
            fact_ids.extend(step_facts)
        if not steps:
            continue
        counters[code] = counters.get(code, 0) + 1
        applies = playbook.get("applies_to") or {}
        region = (
            "、".join(
                REGION_LABEL.get(str(item), str(item)) for item in applies.get("region") or []
            )
            or "全国"
        )
        year = applies.get("year")
        when = f"{year}年，{region}" if year else region
        deadlines = playbook.get("deadlines") or []
        cards.append(
            {
                "id": f"TASK-{code}-{counters[code]:03d}",
                "persona": persona,
                "title": str(playbook.get("title") or ""),
                "when": when,
                "steps": steps,
                "documents": [str(item) for item in playbook.get("documents") or []],
                "deadline": str(deadlines[0]) if deadlines else "",
                "facts": sorted(set(fact_ids)),
                "source": {"kind": "playbook", "id": str(playbook.get("id") or "")},
                "status": "draft",
                "review_due": str(playbook.get("review_due") or ""),
                "note": "generated from an approved playbook; wording review pending",
            }
        )
    return cards


def write_task_cards(cards: list[dict[str, Any]], path: Path | str = DEFAULT_TASK_CARDS) -> None:
    payload = {"schema_version": 1, "updated_at": "2026-11-12", "cards": cards}
    Path(path).write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


__all__ = [
    "DEFAULT_TASK_CARDS",
    "PERSONA_CODE",
    "PERSONAS",
    "STATUSES",
    "TASK_ID",
    "TaskCardError",
    "build_from_playbooks",
    "load_task_cards",
    "validate_task_cards",
    "write_task_cards",
]
